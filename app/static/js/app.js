import { startAudioPlayerWorklet } from "./audio-player.js";
import { startAudioRecorderWorklet, stopMicrophone } from "./audio-recorder.js";

const sessionId = Math.random().toString(36).slice(2, 10);
const wsUrlBase = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/`;
let websocket = null;
let isAudio = false;
let sessionActive = false;
let endAfterTurn = false;
let endReason = "";

const tablesGrid = document.getElementById("tables-grid");
const waitlistList = document.getElementById("waitlist-list");
const connStatus = document.getElementById("conn-status");
const connDot = document.getElementById("conn-dot");
const interactBtn = document.getElementById("interact-btn");
const videos = {
  idle: document.getElementById("vid-idle"),
  listening: document.getElementById("vid-listening"),
  speaking: document.getElementById("vid-speaking"),
};

let audioPlayerNode;
let audioRecorderNode;
let micStream;
let currentAvatar = "idle";
const INACTIVITY_TIMEOUT_MS = 10000;
const SILENCE_THRESHOLD = 700;
let inactivityCheckInterval;
let lastUserSpeechAt = 0;
let lastAgentActivityAt = 0;
let lastTurnCompleteAt = 0;
let speakingFallbackTimeout;
let stopAfterTurnTimeout;
let lastAudioAt = 0;
let pendingTurnComplete = false;
let listeningCheckTimeout;

const setConnStatus = (text, ok = false) => {
  connStatus.textContent = text;
  connDot.style.background = ok ? "#16c782" : "#ffb300";
  connDot.style.boxShadow = ok
    ? "0 0 0 6px rgba(22,199,130,0.18)"
    : "0 0 0 6px rgba(255,179,0,0.18)";
};

const setAvatar = (mode) => {
  if (currentAvatar === mode) return;
  currentAvatar = mode;
  Object.values(videos).forEach((v) => {
    v.classList.remove("active");
    v.pause();
  });
  const target = videos[mode];
  if (!target) return;
  target.classList.add("active");
  // Kick playback on next frame to avoid first-frame glitching
  requestAnimationFrame(() => {
    target.currentTime = 0;
    target.play().catch(() => {});
  });
};
setAvatar("idle");

const renderTables = (tables = []) => {
  if (!Array.isArray(tables) || !tables.length) {
    tablesGrid.innerHTML = `<div class="table-item">No tables</div>`;
    return;
  }
  tablesGrid.innerHTML = tables
    .map(
      (t) => `
      <div class="table-item ${t.status} ${t.status === "occupied" ? "clickable" : ""}" data-table-id="${t.id}">
        <div class="badge ${t.status}">${t.status}</div>
        <div><strong>${t.id}</strong></div>
        <div>${t.seats} seats</div>
        <div>${t.guest_name || "Free"}</div>
      </div>`
    )
    .join("");

  tablesGrid.querySelectorAll(".table-item.occupied").forEach((el) => {
    el.addEventListener("click", () => checkoutTable(el.dataset.tableId));
  });
};

const renderWaitlist = (waitlist = []) => {
  if (!Array.isArray(waitlist) || !waitlist.length) {
    waitlistList.innerHTML = `<div class="wait-item">Empty</div>`;
    return;
  }
  waitlistList.innerHTML = waitlist
    .map(
      (entry, idx) => `
      <div class="wait-item">
        <div>#${idx + 1} • ${entry.name} (${entry.party_size})</div>
        <div>${entry.eta_minutes !== null ? `ETA ${entry.eta_minutes}m` : ""}</div>
      </div>`
    )
    .join("");
};

const fetchStatus = () => {
  fetch(`/api/status?user_id=${sessionId}`)
    .then((res) => res.json())
    .then((data) => {
      renderTables(data.tables || []);
      renderWaitlist(data.waitlist || []);
      if (data.last_event) {
        handleServerEvent(data.last_event);
      }
    })
    .catch((err) => console.error("Status fetch failed", err));
};

const checkoutTable = async (tableId) => {
  if (!tableId) return;
  try {
    const res = await fetch(`/api/checkout?user_id=${sessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ table_id: tableId }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      alert(data.message || "Unable to clear table.");
      return;
    }
    fetchStatus();
  } catch (err) {
    console.error("Checkout failed", err);
  }
};

function connectWebsocket() {
  if (websocket) {
    websocket.onclose = null;
    websocket.onerror = null;
    try {
      websocket.close();
    } catch (e) {}
  }
  const ws_url = `${wsUrlBase}${sessionId}?is_audio=${isAudio}`;
  websocket = new WebSocket(ws_url);

  websocket.onopen = () => {
    setConnStatus("Connected", true);
    if (isAudio) setAvatar("listening");
  };

  websocket.onmessage = (event) => {
    const message_from_server = JSON.parse(event.data);
    console.log("[AGENT TO CLIENT]", message_from_server);

    if (message_from_server.mime_type === "text/plain") {
      markAgentActivity();
      handleTranscript(message_from_server.data || "");
    }

    if (
      message_from_server.interrupted &&
      message_from_server.interrupted === true
    ) {
      if (audioPlayerNode) {
        audioPlayerNode.port.postMessage({ command: "endOfAudio" });
      }
      if (isAudio) {
        setAvatar("listening");
      }
      return;
    }

    if (message_from_server.mime_type === "audio/pcm" && audioPlayerNode) {
      markAgentActivity();
      lastAudioAt = Date.now();
      if (isAudio) setAvatar("speaking");
      audioPlayerNode.port.postMessage(
        base64ToArray(message_from_server.data)
      );
    }

    if (
      message_from_server.turn_complete &&
      message_from_server.turn_complete === true
    ) {
      lastTurnCompleteAt = Date.now();
      markAgentActivity();
      pendingTurnComplete = false;
      clearTimeout(listeningCheckTimeout);
      clearTimeout(speakingFallbackTimeout);
      if (isAudio && sessionActive && !endAfterTurn) {
        setAvatar("listening");
      }
      if (endAfterTurn && isAudio) {
        scheduleStopAfterTurn(endReason || "turn_complete");
      }
    }
  };

  websocket.onclose = () => {
    setConnStatus("Reconnecting…", false);
    setTimeout(connectWebsocket, 2000);
  };

  websocket.onerror = (e) => {
    console.warn("WebSocket error", e);
  };
}

connectWebsocket();

function sendMessage(message) {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send(JSON.stringify(message));
  }
}

function requestStopAfterTurn(reason) {
  endAfterTurn = true;
  if (!endReason) {
    endReason = reason;
  }
}

function markAgentActivity() {
  lastAgentActivityAt = Date.now();
}

function base64ToArray(base64) {
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

let audioRecorderContext;

function startAudio() {
  setAvatar("listening");
  sessionActive = true;
  endAfterTurn = false;
  endReason = "";
  lastTurnCompleteAt = 0;
  startInactivityWatch();
  startAudioPlayerWorklet().then(([node, ctx]) => {
    audioPlayerNode = node;
    audioPlayerNode.port.onmessage = (event) => {
      if (event.data?.command === "buffer_empty") {
        if (sessionActive && isAudio && !endAfterTurn) {
          setAvatar("listening");
        }
      }
    };
  });
  startAudioRecorderWorklet(audioRecorderHandler).then(
    ([node, ctx, stream]) => {
      audioRecorderNode = node;
      audioRecorderContext = ctx;
      micStream = stream;
    }
  );
}

function stopAudioFlow(_reason) {
  sessionActive = false;
  isAudio = false;
  endAfterTurn = false;
  endReason = "";
  lastTurnCompleteAt = 0;
  pendingTurnComplete = false;
  clearTimeout(speakingFallbackTimeout);
  clearTimeout(stopAfterTurnTimeout);
  clearTimeout(listeningCheckTimeout);
  clearInterval(inactivityCheckInterval);
  inactivityCheckInterval = null;
  if (micStream) {
    stopMicrophone(micStream);
    micStream = null;
  }
  if (audioRecorderContext) {
    try {
      audioRecorderContext.close();
    } catch (e) {}
    audioRecorderContext = null;
  }
  if (audioPlayerNode) {
    try {
      audioPlayerNode.disconnect();
    } catch (e) {}
    audioPlayerNode = null;
  }
  interactBtn.disabled = false;
  setAvatar("idle");
}

interactBtn.addEventListener("click", () => {
  interactBtn.disabled = true;
  startAudio();
  isAudio = true;
  connectWebsocket(); // reconnect with audio flag
});

function audioRecorderHandler(pcmData) {
  monitorMicActivity(pcmData);
  sendMessage({
    mime_type: "audio/pcm",
    data: arrayBufferToBase64(pcmData),
  });
}

function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

function monitorMicActivity(pcmBuffer) {
  if (!sessionActive) return;
  const pcm = new Int16Array(pcmBuffer);
  let peak = 0;
  for (let i = 0; i < pcm.length; i++) {
    const magnitude = Math.abs(pcm[i]);
    if (magnitude > peak) peak = magnitude;
  }
  if (peak > SILENCE_THRESHOLD) {
    lastUserSpeechAt = Date.now();
  }
}

function startInactivityWatch() {
  lastAgentActivityAt = Date.now();
  lastUserSpeechAt = Date.now();
  if (inactivityCheckInterval) {
    clearInterval(inactivityCheckInterval);
  }
  inactivityCheckInterval = setInterval(() => {
    if (!sessionActive) return;
    const lastInteraction = Math.max(lastAgentActivityAt, lastUserSpeechAt);
    if (Date.now() - lastInteraction > INACTIVITY_TIMEOUT_MS) {
      stopAudioFlow("inactive");
    }
  }, 1000);
}

function handleServerEvent(event) {
  if (!event || !event.type) return;
  if (event.type === "table_assigned") {
    requestStopAfterTurn("reservation_complete");
    if (isAudio) {
      // Wait for the agent to finish speaking; fall back to a gentle timeout.
      scheduleStopAfterTurn(endReason || "reservation_complete");
    }
  }
}

function handleTranscript(text) {
  if (!text) return;
  const goodbyePattern =
    /\b(goodbye|see you|see ya|take care|talk to you later|bye)\b/i;
  if (goodbyePattern.test(text)) {
    requestStopAfterTurn("goodbye");
  }
}

function scheduleListeningFallback() {
  clearTimeout(speakingFallbackTimeout);
  speakingFallbackTimeout = setTimeout(() => {
    if (
      sessionActive &&
      isAudio &&
      !endAfterTurn &&
      Date.now() - lastAudioAt > 1500
    ) {
      setAvatar("listening");
    }
  }, 2000);
}

function scheduleListeningAfterAudio() {
  clearTimeout(listeningCheckTimeout);
  listeningCheckTimeout = setTimeout(function check() {
    if (!pendingTurnComplete) return;
    const silentFor = Date.now() - lastAudioAt;
    if (silentFor > 500) {
      pendingTurnComplete = false;
      if (sessionActive && isAudio && !endAfterTurn) {
        setAvatar("listening");
      }
    } else {
      listeningCheckTimeout = setTimeout(check, 200);
    }
  }, 300);
}

function scheduleStopAfterTurn(reason) {
  clearTimeout(stopAfterTurnTimeout);
  stopAfterTurnTimeout = setTimeout(() => {
    stopAudioFlow(reason);
  }, 3000);
}

// Initial dashboard and periodic refresh
fetchStatus();
setInterval(fetchStatus, 4000);
