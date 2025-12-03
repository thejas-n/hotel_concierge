# Maitre D — Concierge Demo

A lightweight concierge agent that can seat guests, manage a waitlist, and answer venue questions grounded in `knowledge/mg_cafe.md`. Audio/UI lives under `app/static`, backend under `app/` and `services/`.

## Quick architecture tour
- Frontend: `app/static` serves a single-page UI with video avatars (idle/listening/speaking) and audio streaming.
- Backend API: FastAPI in `app/main.py` exposes `/ws/{user_id}` for BIDI audio/text and `/api/status` for dashboard data.
- Agent: `app/concierge/agent.py` wires tools (availability, add_guest, status, knowledge, Google Search for time).
- Domain logic: `services/` handles hotel state, waitlist, knowledge tool, and updates.
- Knowledge: `app/knowledge/mg_cafe.md` is the ground truth for venue details.
- Streaming: Uses ADK BIDI mode (`StreamingMode.BIDI`) for live audio/text turns; client talks over `/ws/{user_id}`.

## Run locally
1. Install deps in the venv: `pip install -r app/requirements.txt`
2. Set your API key in `app/.env` (`GOOGLE_API_KEY`, `DEMO_AGENT_MODEL` from ListModels).
3. Start the server: `cd app && ../.venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`
4. Open `http://localhost:8000` for the UI (ADK web UI is on `:8080` if you start it).

## What it does
- Gathers name + party size, checks availability, seats or waitlists via tools.
- Grounded venue answers via `get_mg_cafe_knowledge`.
- Supports audio streaming with avatars (idle/listening/speaking).

## Observability: Logging, Tracing, Metrics
- Logging: Python logging to stdout at INFO.
- Tracing: OpenTelemetry tracer/provider with console span exporter; spans around session startup and websocket lifecycle.
- Metrics: OpenTelemetry meter with console exporter; counts WebSocket connections and records model/tool latencies.
Swap exporters (e.g., OTLP) via env if you want to ship data to your observability stack.
