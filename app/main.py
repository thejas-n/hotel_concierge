import os
import json
import asyncio
import base64
import warnings
import logging
import time

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from google.genai import types
from google.genai.types import (
    Part,
    Content,
    Blob,
)

from google.adk.runners import Runner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.websockets import WebSocketDisconnect

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

from concierge.agent import root_agent
from services.state_registry import ensure_manager, set_current_session, get_current_manager

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

APP_NAME = "maitre_d"

session_service = InMemorySessionService()

runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)

async def start_agent_session(user_id, is_audio=False):
    """Starts an agent session"""
    session_id = f"{APP_NAME}_{user_id}"
    session = await runner.session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if not session:
        session = await runner.session_service.create_session(
            app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    model_name = root_agent.model if isinstance(root_agent.model, str) else root_agent.model.model
    is_native_audio = "native-audio" in model_name.lower()

    modality = "AUDIO" if (is_audio or is_native_audio) else "TEXT"

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=[modality],
        session_resumption=types.SessionResumptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig() if (is_audio or is_native_audio) else None,
    )

    live_request_queue = LiveRequestQueue()

    live_events = runner.run_live(
        user_id=user_id,
        session_id=session.id,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return session.id, live_events, live_request_queue


async def agent_to_client_messaging(websocket, live_events):
    """Agent to client communication."""
    try:
        async for event in live_events:
            start_ts = time.time()
            if event.output_transcription and event.output_transcription.text:
                transcript_text = event.output_transcription.text
                message = {
                    "mime_type": "text/plain",
                    "data": transcript_text,
                    "is_transcript": True
                }
                await websocket.send_text(json.dumps(message))
                print(f"[AGENT TO CLIENT]: audio transcript: {transcript_text}")

            part: Part = (
                event.content and event.content.parts and event.content.parts[0]
            )
            if part:
                is_audio = part.inline_data and part.inline_data.mime_type.startswith("audio/pcm")
                if is_audio:
                    audio_data = part.inline_data and part.inline_data.data
                    if audio_data:
                        message = {
                            "mime_type": "audio/pcm",
                            "data": base64.b64encode(audio_data).decode("ascii")
                        }
                        await websocket.send_text(json.dumps(message))
                        print(f"[AGENT TO CLIENT]: audio/pcm: {len(audio_data)} bytes.")

                    if part.text and event.partial:
                        message = {
                            "mime_type": "text/plain",
                            "data": part.text
                        }
                        await websocket.send_text(json.dumps(message))
                        print(f"[AGENT TO CLIENT]: text/plain: {message}")

            # If the turn complete or interrupted, send it
            if event.turn_complete or event.interrupted:
                message = {
                    "turn_complete": event.turn_complete,
                    "interrupted": event.interrupted,
                }
                await websocket.send_text(json.dumps(message))
                print(f"[AGENT TO CLIENT]: {message}")

            latency_ms = (time.time() - start_ts) * 1000
            model_latency_hist.record(latency_ms, attributes={"event": "live_event"})
            logging.info("Model event latency %.1f ms", latency_ms)
    except WebSocketDisconnect:
        print("Client disconnected from agent_to_client_messaging")
    except Exception as e:
        print(f"Error in agent_to_client_messaging: {e}")


async def client_to_agent_messaging(websocket, live_request_queue, session_id: str):
    """Client to agent communication."""
    try:
        while True:
            message_json = await websocket.receive_text()
            message = json.loads(message_json)
            mime_type = message["mime_type"]
            data = message["data"]

            set_current_session(session_id)

            if mime_type == "text/plain":
                content = Content(role="user", parts=[Part.from_text(text=data)])
                start_ts = time.time()
                live_request_queue.send_content(content=content)
                model_latency_hist.record(
                    (time.time() - start_ts) * 1000,
                    attributes={"direction": "client_to_agent", "type": "text"},
                )
                print(f"[CLIENT TO AGENT]: {data}")
            elif mime_type == "audio/pcm":
                decoded_data = base64.b64decode(data)
                start_ts = time.time()
                live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
                model_latency_hist.record(
                    (time.time() - start_ts) * 1000,
                    attributes={"direction": "client_to_agent", "type": "audio"},
                )
            else:
                raise ValueError(f"Mime type not supported: {mime_type}")
    except WebSocketDisconnect:
        print("Client disconnected from client_to_agent_messaging")
    except Exception as e:
        print(f"Error in client_to_agent_messaging: {e}")


app = FastAPI()

STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def setup_observability() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    resource = Resource(attributes={"service.name": APP_NAME})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(ConsoleMetricExporter())],
    )
    metrics.set_meter_provider(meter_provider)


setup_observability()
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
ws_connection_counter = meter.create_counter(
    name="websocket_connections_total",
    unit="1",
    description="Total websocket connections accepted",
)
tool_call_counter = meter.create_counter(
    name="tool_calls_total",
    unit="1",
    description="Total tool calls sent to the model",
)
tool_latency_hist = meter.create_histogram(
    name="tool_call_latency_ms",
    unit="ms",
    description="Latency for tool calls",
)
model_latency_hist = meter.create_histogram(
    name="model_response_latency_ms",
    unit="ms",
    description="Model response latency per event",
)


@app.get("/")
async def root():
    """Serves the index.html"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, is_audio: str):
    """Client websocket endpoint."""

    await websocket.accept()
    ws_connection_counter.add(1)
    logging.info("Client #%s connected, audio mode: %s", user_id, is_audio)

    user_id_str = str(user_id)
    with tracer.start_as_current_span("start_agent_session"):
        session_id, live_events, live_request_queue = await start_agent_session(
            user_id_str, is_audio == "true"
        )
    ensure_manager(session_id)
    set_current_session(session_id)

    # Run bidirectional messaging concurrently
    agent_to_client_task = asyncio.create_task(
        agent_to_client_messaging(websocket, live_events)
    )
    client_to_agent_task = asyncio.create_task(
        client_to_agent_messaging(websocket, live_request_queue, session_id)
    )

    try:
        # Wait for either task to complete (connection close or error)
        tasks = [agent_to_client_task, client_to_agent_task]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        # Check for errors in completed tasks
        for task in done:
            if task.exception() is not None:
                print(f"Task error for client #{user_id}: {task.exception()}")
                import traceback
                traceback.print_exception(type(task.exception()), task.exception(), task.exception().__traceback__)
    finally:
        # Clean up resources (always runs, even if asyncio.wait fails)
        live_request_queue.close()
        print(f"Client #{user_id} disconnected")


def _manager_for_user(user_id: str):
    """Ensure and bind a HotelManager for a given user/session."""
    session_id = f"{APP_NAME}_{user_id}"
    ensure_manager(session_id)
    set_current_session(session_id)
    return get_current_manager()


@app.get("/api/status")
async def status(user_id: str = "ui"):
    manager = _manager_for_user(user_id)
    return manager.get_status()


@app.post("/api/checkout")
async def checkout(payload: dict, user_id: str = "ui"):
    table_id = payload.get("table_id")
    if not table_id:
        return {"success": False, "message": "table_id is required"}
    manager = _manager_for_user(user_id)
    return manager.checkout_and_fill_waitlist(table_id)
