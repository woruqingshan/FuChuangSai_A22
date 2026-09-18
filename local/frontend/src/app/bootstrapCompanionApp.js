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
  transport: "Preparing Service",
  remoteStatus: "Connecting to AI Service",
  inputMode: "text",
  emotionStyle: "supportive",
  facialExpression: "neutral",
  headMotion: "steady",
  audioStatus: "Waiting for Voice Input",
  videoStatus: "Camera Off",
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
        <a class="home-link" href="/">← OneCompanion</a>
        <h1>AI Companion</h1>
      </div>
      <div class="topbar-meta">
        <span class="chip">Multimodal Interaction</span>
        <span class="chip">Digital Human</span>
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
        <p class="eyebrow">Demo Access</p>
        <h2>Enter Access Code</h2>
        <p>An access code is required to use the current demo service.</p>
        <label>
          <span>Access Code</span>
          <input type="password" autocomplete="off" data-role="access-code" placeholder="Enter access code" />
        </label>
        <button type="submit">Enter Demo</button>
        <p class="access-error" data-role="access-error" aria-live="polite"></p>
      </form>
    </div>
    <div class="access-modal-backdrop hidden" data-role="auth-gate">
      <form class="access-modal auth-modal" data-role="auth-form">
        <p class="eyebrow" data-role="auth-eyebrow">Account</p>
        <h2 data-role="auth-title">Sign In</h2>
        <p data-role="auth-description">Sign in to keep your persistent user identity across future interactions.</p>
        <label>
          <span>Username</span>
          <input type="text" autocomplete="username" data-role="auth-username" placeholder="Enter username" />
        </label>
        <label>
          <span>Password</span>
          <input type="password" autocomplete="current-password" data-role="auth-password" placeholder="Enter password" />
        </label>
        <button type="submit" data-role="auth-submit">Sign In</button>
        <button type="button" class="modal-secondary-button" data-role="auth-cancel">Cancel</button>
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
  transport: "Preparing Service",
  remoteStatus: "Connecting to AI Service",
  audioStatus: "Waiting for Voice Input",
  videoStatus: "Camera Off",
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
    chatPanel.addSystemMessage("The service is preparing. Please try again shortly.");
    return false;
  }

  if (!state.hasAccess) {
    chatPanel.addSystemMessage("Enter an access code first.");
    accessGate.show();
    inputBar.setBusy(true);
    return false;
  }

  if (state.isSending) {
    chatPanel.addSystemMessage("The previous interaction is still processing. Please wait.");
    return false;
  }

  const hasText = Boolean(text);
  const hasAudio = Boolean(audio?.audio_base64);
  const hasVideo = Boolean(video?.video_frames?.length || video?.video_meta);

  if (!hasText && !hasAudio) {
    chatPanel.addSystemMessage("Type a message or record a voice message first.");
    return false;
  }

  const turnId = state.nextTurnId;
  const inputMode = hasAudio ? "audio" : "text";
  const userMessage = hasText ? text : "[Voice Message]";

  chatPanel.addMessage({
    role: "user",
    text: userMessage,
    meta: formatMessageMeta({ turnId, inputMode }),
  });

  state.isSending = true;
  inputBar.setBusy(true);
  chatPanel.setLoading(true);
  syncStatus({
    transport: "Sending Request",
    remoteStatus: "Waiting for AI Response",
    inputMode,
    audioStatus: hasAudio ? `Voice attached (${audio.audio_duration_ms} ms)` : "Text Input",
    videoStatus: hasVideo
      ? `${video.video_frames?.length || video.video_meta?.sampled_frame_count || 0} video frames attached`
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
    state.transport = "Waiting for Avatar Response";
    syncStatus({
      transport: state.transport,
      remoteStatus: "Text and audio are ready. Generating synchronized avatar video.",
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
        : "Avatar video generation failed";
      chatPanel.addSystemMessage(`The text response was preserved, but ${videoError}`);
    }
    syncStatus({
      transport: avatarRenderResult?.status === "failed"
        ? "Response complete; avatar video generation failed"
        : "Response and avatar are ready",
      remoteStatus: response.server_status === "ok" ? "AI Service Connected" : "AI Service Error",
      inputMode: response.input_mode || inputMode,
      emotionStyle: response.emotion_style,
      facialExpression: response.avatar_action.facial_expression,
      headMotion: response.avatar_action.head_motion,
      audioStatus: hasAudio ? "Voice Processed" : "Text Processed",
      videoStatus: hasVideo ? "Visual Keyframes Processed" : state.videoStatus,
    });
    return true;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown request error";
    if (error?.status === 401) {
      state.isSessionReady = false;
      state.hasAccess = false;
      inputBar.setBusy(true);
      chatPanel.addSystemMessage("The connection expired. Reconnecting to the service; please resend your last message.");
      await initializeSession({ showReadyMessage: false });
    } else if (error?.status === 403) {
      state.hasAccess = false;
      inputBar.setBusy(true);
      accessGate.show();
      chatPanel.addSystemMessage("Enter an access code first.");
    } else if (error?.status === 409) {
      chatPanel.addSystemMessage("An interaction is already processing. Please wait for it to finish.");
    } else if (error?.status === 429 && error?.reason === "queue_full") {
      chatPanel.addSystemMessage("The demo is busy. Please try again shortly.");
    } else if (error?.status === 429) {
      chatPanel.addSystemMessage("Too many attempts. Please try again later.");
    } else {
      chatPanel.addSystemMessage(`Request failed: ${detail}`);
    }
    syncStatus({
      transport: "Request Failed",
      remoteStatus: "AI Service temporarily unavailable. Please try again shortly.",
      audioStatus: hasAudio ? "Voice Send Failed" : "Text Send Failed",
      videoStatus: hasVideo ? "Visual Input Send Failed" : state.videoStatus,
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
    chatPanel.addSystemMessage("Service initialization failed. Refresh the page and try again.");
    syncStatus({
      transport: "Service Initialization Failed",
      remoteStatus: "Service Connection Error",
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
      transport: "Waiting for First Interaction",
      remoteStatus: "AI Service Connected",
    });
    if (showReadyMessage) {
      chatPanel.addSystemMessage("OneCompanion is ready. Type a message or use voice input to begin.");
    }
  } else {
    accessGate.show();
    syncStatus({
      transport: "Waiting for Access Code",
      remoteStatus: "AI Service Connected",
    });
  }
}

function handleJobStatus(job) {
  if (!job?.status) {
    return;
  }
  if (job.status === "queued") {
    syncStatus({
      transport: `Queued: position ${job.queue_position || 1}`,
      remoteStatus: "Waiting to Generate",
    });
    return;
  }
  if (job.status === "processing") {
    syncStatus({
      transport: "Generating Response",
      remoteStatus: "AI Service Processing",
    });
    return;
  }
  if (job.status === "rendering") {
    syncStatus({
      transport: "Waiting for Avatar Response",
      remoteStatus: "Text and audio are ready. Generating synchronized avatar video.",
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
      errorText.textContent = "Enter an access code.";
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
        transport: "Waiting for First Interaction",
        remoteStatus: "AI Service Connected",
      });
      chatPanel.addSystemMessage("OneCompanion is ready. Type a message or use voice input to begin.");
      inputBar.setBusy(state.isSending || !isInteractionReady());
    } catch (error) {
      errorText.textContent = error?.status === 429
        ? "Too many attempts. Please try again later."
        : "The access code is invalid or has expired.";
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
        chatPanel.addSystemMessage("Complete access code verification first.");
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
        chatPanel.addSystemMessage("You have signed out. The current anonymous session can continue.");
      } catch (error) {
        chatPanel.addSystemMessage("Sign out failed. Please try again shortly.");
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
      errorText.textContent = "Enter both username and password.";
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
      chatPanel.addSystemMessage(mode === "register" ? "Registration successful. You are now signed in." : "Signed in successfully.");
    } catch (error) {
      if (mode === "register" && error?.status === 403) {
        errorText.textContent = "Complete access code verification first.";
      } else if (error?.status === 409) {
        errorText.textContent = "This username is already registered.";
      } else if (error?.status === 429) {
        errorText.textContent = "Too many attempts. Please try again later.";
      } else {
        errorText.textContent = error?.message || "Account operation failed. Please try again later.";
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
    title.textContent = isRegister ? "Create Account" : "Sign In";
    description.textContent = isRegister
      ? "Your current session will be linked to your persistent user identity."
      : "Sign in to keep your persistent user identity across future interactions.";
    submitButton.textContent = isRegister ? "Register and Sign In" : "Sign In";
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
        <button type="button" class="account-link" data-action="logout">Sign Out</button>
      `;
      return;
    }
    element.innerHTML = `
      <button type="button" class="account-link" data-action="login">Sign In</button>
      <button type="button" class="account-primary" data-action="register">Register</button>
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
