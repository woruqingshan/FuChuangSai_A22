import "./styles.css";

import { sendChatRequest } from "./api/chat";
import { createAvatarPanel } from "./ui/AvatarPanel";
import { createChatPanel } from "./ui/ChatPanel";
import { formatAssistantMeta, formatMessageMeta } from "./ui/displayText";
import { createInputBar } from "./ui/InputBar";
import { createStatusBar } from "./ui/StatusBar";

const app = document.getElementById("app");

const DEFAULT_AVATAR_SESSION_ID = "demo_s1";
const DEFAULT_AVATAR_STREAM_ID = "demo_stream_1";

const configuredSessionId = (import.meta.env.VITE_AVATAR_SESSION_ID || "").trim();
const configuredStreamId = (import.meta.env.VITE_AVATAR_STREAM_ID || "").trim();

function resolveTabSessionId(baseSessionId) {
  if (import.meta.env.VITE_UNIQUE_SESSION_PER_TAB !== "true") {
    return baseSessionId;
  }
  const storageKey = "a22.avatar.tab_session_suffix";
  try {
    let suffix = sessionStorage.getItem(storageKey);
    if (!suffix) {
      suffix = crypto.randomUUID().replace(/-/g, "").slice(0, 8);
      sessionStorage.setItem(storageKey, suffix);
    }
    return `${baseSessionId}-${suffix}`;
  } catch {
    return `${baseSessionId}-${Date.now().toString(36)}`;
  }
}

const state = {
  sessionId: resolveTabSessionId(configuredSessionId || DEFAULT_AVATAR_SESSION_ID),
  streamId: configuredStreamId || DEFAULT_AVATAR_STREAM_ID,
  nextTurnId: 1,
  transport: "Waiting for first message",
  remoteStatus: "Remote link pending",
  inputMode: "text",
  emotionStyle: "supportive",
  facialExpression: "neutral",
  headMotion: "steady",
  audioStatus: "Audio idle",
  videoStatus: "Camera disabled",
  isSending: false,
  cameraEnabled: false,
  avatarProfileId: "avatar_a",
};

let leftTopStack = null;

const avatarPanel = createAvatarPanel({
  onProfileChange: (profile) => {
    state.avatarProfileId = profile?.id || state.avatarProfileId;
  },
});
state.avatarProfileId = avatarPanel.getSelectedProfileId();
const chatPanel = createChatPanel();
const statusBar = createStatusBar();
const inputBar = createInputBar({
  onSend: handleSend,
  onStatusChange: (audioStatus) => {
    syncStatus({
      audioStatus,
    });
  },
  onVideoStatusChange: (videoStatus) => {
    syncStatus({
      videoStatus,
    });
  },
  onCameraModeChange: (cameraEnabled) => {
    state.cameraEnabled = cameraEnabled;
    syncLayout();
  },
});

app.innerHTML = `
  <div class="page-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">A22 情感陪伴系统</p>
        <h1>情感陪伴数字人助手</h1>
      </div>
      <div class="topbar-meta">
        <span class="chip">本地轻量处理</span>
        <span class="chip">远端智能推理</span>
      </div>
    </header>
    <main class="workspace-grid">
      <section class="left-column">
        <section class="left-top-stack camera-off"></section>
        <section class="control-column panel"></section>
      </section>
      <section class="right-column">
        <section class="avatar-column"></section>
        <section class="status-column panel"></section>
      </section>
    </main>
  </div>
`;

leftTopStack = app.querySelector(".left-top-stack");
leftTopStack.append(inputBar.mediaElement, chatPanel.element);
app.querySelector(".control-column").append(inputBar.controlsElement);
app.querySelector(".avatar-column").appendChild(avatarPanel.element);
app.querySelector(".status-column").appendChild(statusBar.element);

chatPanel.addSystemMessage("界面已准备好。请输入文字，或点击语音按钮开始对话。");
syncStatus({
  remoteStatus: "Remote link pending",
  audioStatus: "Audio idle",
  videoStatus: "Camera disabled",
});
syncLayout();

function buildTextTurnTimeWindow(turnId) {
  const now = Date.now();
  return {
    window_id: `${state.sessionId}-turn-${turnId}`,
    source_clock: "browser_epoch_ms",
    transport_mode: "http_turn",
    stream_id: state.streamId,
    sequence_id: turnId,
    capture_started_at_ms: now,
    capture_ended_at_ms: now,
    window_duration_ms: 0,
  };
}

async function handleSend({ text, audio, video }) {
  if (state.isSending) {
    chatPanel.addSystemMessage("上一轮还在处理中，请稍等。");
    return false;
  }

  const hasText = Boolean(text);
  const hasAudio = Boolean(audio?.audio_base64);
  const hasVideo = Boolean(video?.video_frames?.length || video?.video_meta);

  if (!hasText && !hasAudio) {
    chatPanel.addSystemMessage("请先输入文字，或录制一段语音。");
    return false;
  }

  const turnId = state.nextTurnId;
  const inputMode = hasAudio ? "audio" : "text";
  const userMessage = hasText ? text : "[语音消息]";

  chatPanel.addMessage({
    role: "user",
    text: userMessage,
    meta: formatMessageMeta({ turnId, inputMode }),
  });

  state.isSending = true;
  inputBar.setBusy(true);
  chatPanel.setLoading(true);
  syncStatus({
    transport: "Sending request to local edge-backend",
    remoteStatus: "Awaiting remote orchestrator response",
    inputMode,
    audioStatus: hasAudio ? `已附带语音（${audio.audio_duration_ms} 毫秒）` : "Text only",
    videoStatus: hasVideo
      ? `已附带 ${video.video_frames?.length || video.video_meta?.sampled_frame_count || 0} 帧视频画面`
      : state.videoStatus,
  });

  try {
    const baseTurnTimeWindow = video?.turn_time_window
      || (hasAudio ? audio.turn_time_window : buildTextTurnTimeWindow(turnId));
    const turnTimeWindow = {
      ...(baseTurnTimeWindow || {}),
      window_id: baseTurnTimeWindow?.window_id || `${state.sessionId}-turn-${turnId}`,
      source_clock: baseTurnTimeWindow?.source_clock || "browser_epoch_ms",
      transport_mode: baseTurnTimeWindow?.transport_mode || "http_turn",
      stream_id: state.streamId,
      sequence_id: turnId,
    };
    const requestPayload = {
      session_id: state.sessionId,
      turn_id: turnId,
      user_text: hasText ? text : undefined,
      input_type: inputMode,
      client_ts: Math.floor(Date.now() / 1000),
      turn_time_window: turnTimeWindow,
      avatar_profile_id: state.avatarProfileId,
    };

    if (hasAudio) {
      const { turn_time_window: _ignoredAudioWindow, ...audioPayload } = audio;
      Object.assign(requestPayload, audioPayload);
    }

    if (hasVideo) {
      const { turn_time_window: _ignoredVideoWindow, ...videoPayload } = video;
      Object.assign(requestPayload, videoPayload);
    }

    const response = await sendChatRequest(requestPayload);

    state.nextTurnId += 1;
    state.transport = "Waiting for synchronized digital-human video";
    syncStatus({
      transport: state.transport,
      remoteStatus: "Text and audio ready; rendering digital-human video",
    });

    const avatarRenderResult = await avatarPanel.update(response).catch((error) => ({
      status: "failed",
      error,
    }));

    chatPanel.addMessage({
      role: "assistant",
      text: response.reply_text,
      meta: formatAssistantMeta({
        emotionStyle: response.emotion_style,
        facialExpression: response.avatar_action.facial_expression,
        headMotion: response.avatar_action.head_motion,
      }),
    });
    if (avatarRenderResult?.status === "failed") {
      const videoError = avatarRenderResult.error instanceof Error
        ? avatarRenderResult.error.message
        : "数字人视频生成失败";
      chatPanel.addSystemMessage(`文本回复已保留，但${videoError}`);
    }
    syncStatus({
      transport: avatarRenderResult?.status === "failed"
        ? "Text reply received; digital-human video failed"
        : "Text and digital-human video ready",
      remoteStatus: response.server_status === "ok" ? "Remote orchestrator connected" : "Remote orchestrator error",
      inputMode: response.input_mode || inputMode,
      emotionStyle: response.emotion_style,
      facialExpression: response.avatar_action.facial_expression,
      headMotion: response.avatar_action.head_motion,
      audioStatus: hasAudio ? "Audio processed by edge-backend" : "Text turn processed",
      videoStatus: hasVideo ? "Video key frames forwarded by edge-backend" : state.videoStatus,
    });
    return true;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "未知请求错误";
    chatPanel.addSystemMessage(`请求失败：${detail}`);
    syncStatus({
      transport: "Request failed",
      remoteStatus: "Check edge-backend and remote orchestrator",
      audioStatus: hasAudio ? "Audio send failed" : "Text send failed",
      videoStatus: hasVideo ? "Video send failed" : state.videoStatus,
    });
    return false;
  } finally {
    state.isSending = false;
    inputBar.setBusy(false);
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
  state.videoStatus = nextState.videoStatus || state.videoStatus;
  statusBar.update({
    sessionId: state.sessionId,
    streamId: state.streamId,
    nextTurnId: state.nextTurnId,
    transport: state.transport,
    remoteStatus: state.remoteStatus,
    inputMode: state.inputMode,
    emotionStyle: state.emotionStyle,
    facialExpression: state.facialExpression,
    headMotion: state.headMotion,
    audioStatus: state.audioStatus,
    videoStatus: state.videoStatus,
  });
}

function syncLayout() {
  if (!leftTopStack) {
    return;
  }
  leftTopStack.classList.toggle("camera-on", state.cameraEnabled);
  leftTopStack.classList.toggle("camera-off", !state.cameraEnabled);
}
