import { fetchAccessStatus, verifyAccessCode } from "../api/access";
import { fetchAuthMe, loginAccount, logoutAccount, registerAccount } from "../api/auth";
import { sendChatRequest } from "../api/chat";
import { bootstrapServerSession } from "../api/session";
import { createAvatarPanel } from "../ui/AvatarPanel";
import { createChatPanel } from "../ui/ChatPanel";
import { formatAssistantMeta, formatMessageMeta } from "../ui/displayText";
import { createInputBar } from "../ui/InputBar";
import { createStatusBar } from "../ui/StatusBar";

export function bootstrapCompanionApp({ root = document.getElementById("app") } = {}) {
const app = root;
if (!app) {
  return;
}

const state = {
  sessionId: "",
  streamId: "",
  nextTurnId: 1,
  transport: "正在准备服务",
  remoteStatus: "AI 服务连接中",
  inputMode: "text",
  emotionStyle: "supportive",
  facialExpression: "neutral",
  headMotion: "steady",
  audioStatus: "语音待输入",
  videoStatus: "摄像头未开启",
  isSending: false,
  isSessionReady: false,
  hasAccess: false,
  authUser: null,
  cameraEnabled: false,
  avatarProfileId: "avatar_a",
};

let leftTopStack = null;
let accessGate = null;
let accountMenu = null;

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
  <div class="page-shell app-page-shell">
    <header class="topbar">
      <div>
        <a class="home-link" href="/">← 知心伴行</a>
        <h1>AI 情感陪护数字人</h1>
      </div>
      <div class="topbar-meta">
        <span class="chip">多模态陪伴</span>
        <span class="chip">数字人表达</span>
        <div class="account-entry" data-role="account-entry"></div>
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
    <div class="access-modal-backdrop hidden" data-role="access-gate">
      <form class="access-modal" data-role="access-form">
        <p class="eyebrow">体验入口</p>
        <h2>请输入体验邀请码</h2>
        <p>当前数字人服务需要邀请码后才能开始体验。</p>
        <label>
          <span>邀请码</span>
          <input type="password" autocomplete="off" data-role="access-code" placeholder="请输入邀请码" />
        </label>
        <button type="submit">进入体验</button>
        <p class="access-error" data-role="access-error" aria-live="polite"></p>
      </form>
    </div>
    <div class="access-modal-backdrop hidden" data-role="auth-gate">
      <form class="access-modal auth-modal" data-role="auth-form">
        <p class="eyebrow" data-role="auth-eyebrow">账号</p>
        <h2 data-role="auth-title">登录账号</h2>
        <p data-role="auth-description">登录后可为后续长期陪伴能力保留用户身份。</p>
        <label>
          <span>用户名</span>
          <input type="text" autocomplete="username" data-role="auth-username" placeholder="请输入用户名" />
        </label>
        <label>
          <span>密码</span>
          <input type="password" autocomplete="current-password" data-role="auth-password" placeholder="请输入密码" />
        </label>
        <button type="submit" data-role="auth-submit">登录</button>
        <button type="button" class="modal-secondary-button" data-role="auth-cancel">取消</button>
        <p class="access-error" data-role="auth-error" aria-live="polite"></p>
      </form>
    </div>
  </div>
`;

leftTopStack = app.querySelector(".left-top-stack");
leftTopStack.append(inputBar.mediaElement, chatPanel.element);
app.querySelector(".control-column").append(inputBar.controlsElement);
app.querySelector(".avatar-column").appendChild(avatarPanel.element);
app.querySelector(".status-column").appendChild(statusBar.element);
accessGate = createAccessGate(app.querySelector('[data-role="access-gate"]'));
accountMenu = createAccountMenu(
  app.querySelector('[data-role="account-entry"]'),
  app.querySelector('[data-role="auth-gate"]'),
);

inputBar.setBusy(true);
syncStatus({
  transport: "正在准备服务",
  remoteStatus: "AI 服务连接中",
  audioStatus: "语音待输入",
  videoStatus: "摄像头未开启",
});
syncLayout();
void initializeSession();

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
  if (!state.isSessionReady) {
    chatPanel.addSystemMessage("服务正在准备中，请稍后再试。");
    return false;
  }

  if (!state.hasAccess) {
    chatPanel.addSystemMessage("请先输入体验邀请码。");
    accessGate.show();
    inputBar.setBusy(true);
    return false;
  }

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
    transport: "正在发送请求",
    remoteStatus: "等待 AI 服务生成回复",
    inputMode,
    audioStatus: hasAudio ? `已附带语音（${audio.audio_duration_ms} 毫秒）` : "文本输入",
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

    const response = await sendChatRequest(requestPayload, {
      onJobStatus: handleJobStatus,
    });

    state.nextTurnId += 1;
    state.transport = "等待数字人表达生成";
    syncStatus({
      transport: state.transport,
      remoteStatus: "文字与语音已就绪，正在生成同步数字人视频",
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
        ? "文字回复已完成，数字人视频生成失败"
        : "文字与数字人表达已就绪",
      remoteStatus: response.server_status === "ok" ? "AI 服务已连接" : "AI 服务异常",
      inputMode: response.input_mode || inputMode,
      emotionStyle: response.emotion_style,
      facialExpression: response.avatar_action.facial_expression,
      headMotion: response.avatar_action.head_motion,
      audioStatus: hasAudio ? "语音已处理" : "文本已处理",
      videoStatus: hasVideo ? "视觉关键帧已处理" : state.videoStatus,
    });
    return true;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "未知请求错误";
    if (error?.status === 401) {
      state.isSessionReady = false;
      state.hasAccess = false;
      inputBar.setBusy(true);
      chatPanel.addSystemMessage("当前连接已失效，正在重新连接服务。请重新发送上一条消息。");
      await initializeSession({ showReadyMessage: false });
    } else if (error?.status === 403) {
      state.hasAccess = false;
      inputBar.setBusy(true);
      accessGate.show();
      chatPanel.addSystemMessage("请先输入体验邀请码。");
    } else if (error?.status === 409) {
      chatPanel.addSystemMessage("当前已有一轮对话正在处理中，请等待完成。");
    } else if (error?.status === 429 && error?.reason === "queue_full") {
      chatPanel.addSystemMessage("当前体验人数较多，请稍后再试。");
    } else if (error?.status === 429) {
      chatPanel.addSystemMessage("尝试次数过多，请稍后再试。");
    } else {
      chatPanel.addSystemMessage(`请求失败：${detail}`);
    }
    syncStatus({
      transport: "请求失败",
      remoteStatus: "AI 服务暂不可用，请稍后再试",
      audioStatus: hasAudio ? "语音发送失败" : "文本发送失败",
      videoStatus: hasVideo ? "视觉信息发送失败" : state.videoStatus,
    });
    return false;
  } finally {
    state.isSending = false;
    inputBar.setBusy(!isInteractionReady());
    chatPanel.setLoading(false);
  }
}

async function initializeSession({ showReadyMessage = true } = {}) {
  try {
    const session = await bootstrapServerSession();
    state.sessionId = session.session_id || state.sessionId;
    state.streamId = session.stream_id || state.streamId;
    state.nextTurnId = Number(session.next_turn_id || 1);
    state.isSessionReady = true;
    await refreshAccessState({ showReadyMessage });
    await refreshAuthState();
  } catch (error) {
    state.isSessionReady = false;
    console.warn("Companion service bootstrap failed", error);
    chatPanel.addSystemMessage("服务初始化失败，请刷新页面后重试。");
    syncStatus({
      transport: "服务初始化失败",
      remoteStatus: "服务连接异常",
    });
  } finally {
    inputBar.setBusy(state.isSending || !isInteractionReady());
  }
}

async function refreshAuthState() {
  try {
    const auth = await fetchAuthMe();
    state.authUser = auth.authenticated ? auth.user : null;
  } catch (error) {
    console.warn("Account status check failed", error);
    state.authUser = null;
  } finally {
    accountMenu?.render();
  }
}

async function refreshAccessState({ showReadyMessage = true } = {}) {
  const access = await fetchAccessStatus();
  state.hasAccess = Boolean(access.authorized);
  if (state.hasAccess) {
    accessGate.hide();
    syncStatus({
      transport: "等待首次对话",
      remoteStatus: "AI 服务已连接",
    });
    if (showReadyMessage) {
      chatPanel.addSystemMessage("知心伴行已准备好。请输入文字，或点击语音按钮开始对话。");
    }
  } else {
    accessGate.show();
    syncStatus({
      transport: "等待输入邀请码",
      remoteStatus: "AI 服务已连接",
    });
  }
}

function handleJobStatus(job) {
  if (!job?.status) {
    return;
  }
  if (job.status === "queued") {
    syncStatus({
      transport: `当前正在排队，第 ${job.queue_position || 1} 位`,
      remoteStatus: "等待进入生成",
    });
    return;
  }
  if (job.status === "processing") {
    syncStatus({
      transport: "正在生成回复",
      remoteStatus: "AI 服务正在处理",
    });
    return;
  }
  if (job.status === "rendering") {
    syncStatus({
      transport: "等待数字人表达生成",
      remoteStatus: "文字与语音已就绪，正在生成同步数字人视频",
    });
  }
}

function isInteractionReady() {
  return state.isSessionReady && state.hasAccess;
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

function createAccessGate(element) {
  const form = element.querySelector('[data-role="access-form"]');
  const input = element.querySelector('[data-role="access-code"]');
  const errorText = element.querySelector('[data-role="access-error"]');
  const submitButton = form.querySelector('button[type="submit"]');

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const code = input.value.trim();
    if (!code) {
      errorText.textContent = "请输入体验邀请码。";
      return;
    }
    submitButton.disabled = true;
    input.disabled = true;
    errorText.textContent = "";
    try {
      await verifyAccessCode(code);
      input.value = "";
      state.hasAccess = true;
      element.classList.add("hidden");
      syncStatus({
        transport: "等待首次对话",
        remoteStatus: "AI 服务已连接",
      });
      chatPanel.addSystemMessage("知心伴行已准备好。请输入文字，或点击语音按钮开始对话。");
      inputBar.setBusy(state.isSending || !isInteractionReady());
    } catch (error) {
      errorText.textContent = error?.status === 429
        ? "尝试次数过多，请稍后再试。"
        : "邀请码无效或已失效。";
    } finally {
      submitButton.disabled = false;
      input.disabled = false;
      input.focus();
    }
  });

  return {
    show() {
      element.classList.remove("hidden");
      window.setTimeout(() => input.focus(), 50);
      inputBar.setBusy(true);
    },
    hide() {
      element.classList.add("hidden");
      errorText.textContent = "";
    },
  };
}

function createAccountMenu(element, modalElement) {
  const form = modalElement.querySelector('[data-role="auth-form"]');
  const title = modalElement.querySelector('[data-role="auth-title"]');
  const description = modalElement.querySelector('[data-role="auth-description"]');
  const usernameInput = modalElement.querySelector('[data-role="auth-username"]');
  const passwordInput = modalElement.querySelector('[data-role="auth-password"]');
  const submitButton = modalElement.querySelector('[data-role="auth-submit"]');
  const cancelButton = modalElement.querySelector('[data-role="auth-cancel"]');
  const errorText = modalElement.querySelector('[data-role="auth-error"]');
  let mode = "login";

  element.addEventListener("click", async (event) => {
    const action = event.target?.dataset?.action;
    if (action === "login") {
      show("login");
    }
    if (action === "register") {
      if (!state.hasAccess) {
        chatPanel.addSystemMessage("请先完成体验邀请码验证。");
        accessGate.show();
        return;
      }
      show("register");
    }
    if (action === "logout") {
      try {
        await logoutAccount();
        state.authUser = null;
        render();
        chatPanel.addSystemMessage("已退出账号，当前匿名会话可继续使用。");
      } catch (error) {
        chatPanel.addSystemMessage("退出失败，请稍后再试。");
      }
    }
  });

  cancelButton.addEventListener("click", () => {
    hide();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    if (!username || !password) {
      errorText.textContent = "请输入用户名和密码。";
      return;
    }
    submitButton.disabled = true;
    usernameInput.disabled = true;
    passwordInput.disabled = true;
    errorText.textContent = "";
    try {
      const auth = mode === "register"
        ? await registerAccount({ username, password })
        : await loginAccount({ username, password });
      state.authUser = auth.user || null;
      render();
      hide();
      chatPanel.addSystemMessage(mode === "register" ? "注册成功，已登录。" : "登录成功。");
    } catch (error) {
      if (mode === "register" && error?.status === 403) {
        errorText.textContent = "请先完成体验邀请码验证。";
      } else if (error?.status === 409) {
        errorText.textContent = "用户名已被注册。";
      } else if (error?.status === 429) {
        errorText.textContent = "尝试次数过多，请稍后再试。";
      } else {
        errorText.textContent = error?.message || "账号操作失败，请稍后重试。";
      }
    } finally {
      submitButton.disabled = false;
      usernameInput.disabled = false;
      passwordInput.disabled = false;
      usernameInput.focus();
    }
  });

  function show(nextMode) {
    mode = nextMode;
    const isRegister = mode === "register";
    title.textContent = isRegister ? "注册账号" : "登录账号";
    description.textContent = isRegister
      ? "注册后当前会话会绑定到你的长期用户身份。"
      : "登录后当前会话会绑定到你的长期用户身份。";
    submitButton.textContent = isRegister ? "注册并登录" : "登录";
    errorText.textContent = "";
    passwordInput.value = "";
    modalElement.classList.remove("hidden");
    window.setTimeout(() => usernameInput.focus(), 50);
  }

  function hide() {
    modalElement.classList.add("hidden");
    errorText.textContent = "";
  }

  function render() {
    if (state.authUser) {
      element.innerHTML = `
        <span class="account-name">${escapeHtml(state.authUser.username)}</span>
        <button type="button" class="account-link" data-action="logout">退出</button>
      `;
      return;
    }
    element.innerHTML = `
      <button type="button" class="account-link" data-action="login">登录</button>
      <button type="button" class="account-primary" data-action="register">注册</button>
    `;
  }

  render();
  return { render };
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
}
