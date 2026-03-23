import "./styles.css";

import { sendChatRequest } from "./api/chat";
import { createAvatarPanel } from "./ui/AvatarPanel";
import { createChatPanel } from "./ui/ChatPanel";
import { createInputBar } from "./ui/InputBar";
import { createStatusBar } from "./ui/StatusBar";

const app = document.getElementById("app");

const state = {
  sessionId: `demo-${crypto.randomUUID().slice(0, 8)}`,
  nextTurnId: 1,
  transport: "Waiting for first message",
  remoteStatus: "Remote link pending",
  inputMode: "text",
  emotionStyle: "supportive",
  facialExpression: "neutral",
  headMotion: "steady",
  audioStatus: "Audio idle",
};

const avatarPanel = createAvatarPanel();
const chatPanel = createChatPanel();
const statusBar = createStatusBar();
const inputBar = createInputBar({
  onSend: handleSend,
  onStatusChange: (audioStatus) => {
    syncStatus({
      audioStatus,
    });
  },
});

app.innerHTML = `
  <div class="page-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">A22 Local Workspace</p>
        <h1>Emotion Support Digital Human Console</h1>
      </div>
      <div class="topbar-meta">
        <span class="chip">Local light processing</span>
        <span class="chip">Remote unified reasoning</span>
      </div>
    </header>
    <main class="workspace-grid">
      <section class="avatar-column panel"></section>
      <section class="chat-column panel"></section>
      <section class="control-column panel"></section>
    </main>
  </div>
`;

app.querySelector(".avatar-column").appendChild(avatarPanel.element);
app.querySelector(".chat-column").appendChild(chatPanel.element);
app.querySelector(".control-column").append(statusBar.element, inputBar.element);

chatPanel.addSystemMessage("Local UI is ready. Send text or record a short audio clip to start.");
syncStatus({
  remoteStatus: "Remote link pending",
  audioStatus: "Audio idle",
});

async function handleSend({ text, audio }) {
  const hasText = Boolean(text);
  const hasAudio = Boolean(audio?.audio_base64);

  if (!hasText && !hasAudio) {
    chatPanel.addSystemMessage("Please enter text or record audio before sending.");
    return false;
  }

  const turnId = state.nextTurnId;
  const inputMode = hasAudio ? "audio" : "text";
  const userMessage = hasText ? text : "[Voice message]";

  chatPanel.addMessage({
    role: "user",
    text: userMessage,
    meta: `Turn ${turnId} · ${inputMode}`,
  });

  chatPanel.setLoading(true);
  syncStatus({
    transport: "Sending request to local edge-backend",
    remoteStatus: "Awaiting remote orchestrator response",
    inputMode,
    audioStatus: hasAudio ? `Audio attached (${audio.audio_duration_ms} ms)` : "Text only",
  });

  try {
    const response = await sendChatRequest({
      session_id: state.sessionId,
      turn_id: turnId,
      user_text: hasText ? text : undefined,
      input_type: inputMode,
      client_ts: Math.floor(Date.now() / 1000),
      ...(hasAudio ? audio : {}),
    });

    state.nextTurnId += 1;
    state.transport = "Request completed";

    chatPanel.addMessage({
      role: "assistant",
      text: response.reply_text,
      meta: `${response.emotion_style} · ${response.avatar_action.facial_expression} / ${response.avatar_action.head_motion}`,
    });
    avatarPanel.update(response);
    syncStatus({
      transport: "Remote reply received",
      remoteStatus: response.server_status === "ok" ? "Remote orchestrator connected" : "Remote orchestrator error",
      inputMode: response.input_mode || inputMode,
      emotionStyle: response.emotion_style,
      facialExpression: response.avatar_action.facial_expression,
      headMotion: response.avatar_action.head_motion,
      audioStatus: hasAudio ? "Audio processed by edge-backend" : "Text turn processed",
    });
    return true;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown request error";
    chatPanel.addSystemMessage(`Request failed: ${detail}`);
    syncStatus({
      transport: "Request failed",
      remoteStatus: "Check edge-backend and remote orchestrator",
      audioStatus: hasAudio ? "Audio send failed" : "Text send failed",
    });
    return false;
  } finally {
    chatPanel.setLoading(false);
  }
}

function syncStatus(nextState) {
  state.transport = nextState.transport || state.transport;
  state.remoteStatus = nextState.remoteStatus || state.remoteStatus;
  state.inputMode = nextState.inputMode || state.inputMode;
  state.emotionStyle = nextState.emotionStyle || state.emotionStyle;
  state.facialExpression = nextState.facialExpression || state.facialExpression;
  state.headMotion = nextState.headMotion || state.headMotion;
  state.audioStatus = nextState.audioStatus || state.audioStatus;

  statusBar.update({
    sessionId: state.sessionId,
    nextTurnId: state.nextTurnId,
    transport: state.transport,
    remoteStatus: state.remoteStatus,
    inputMode: state.inputMode,
    emotionStyle: state.emotionStyle,
    facialExpression: state.facialExpression,
    headMotion: state.headMotion,
    audioStatus: state.audioStatus,
  });
}
