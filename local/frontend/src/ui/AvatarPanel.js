import { createAvatarRenderer } from "../avatar/renderer";

const STREAM_URL_STORAGE_KEY = "a22.avatar.external_stream_url";

function normalizeStreamUrl(raw) {
  return String(raw || "").trim();
}

function isLikelyMediaUrl(url) {
  const lower = String(url || "").toLowerCase();
  if (!lower) {
    return false;
  }
  if (lower.startsWith("blob:") || lower.startsWith("data:video/")) {
    return true;
  }
  return [".mp4", ".webm", ".m3u8", ".mov", ".ogg", ".ogv"].some((suffix) => lower.includes(suffix));
}

function readInitialStreamUrl() {
  try {
    const queryUrl = new URLSearchParams(window.location.search).get("avatar_stream");
    if (queryUrl) {
      return normalizeStreamUrl(queryUrl);
    }
  } catch {
    // Ignore malformed query string and keep fallback behavior.
  }

  try {
    return normalizeStreamUrl(localStorage.getItem(STREAM_URL_STORAGE_KEY) || "");
  } catch {
    return "";
  }
}

function persistStreamUrl(url) {
  try {
    if (url) {
      localStorage.setItem(STREAM_URL_STORAGE_KEY, url);
      return;
    }
    localStorage.removeItem(STREAM_URL_STORAGE_KEY);
  } catch {
    // Ignore storage failures in private mode / restricted environments.
  }
}

export function createAvatarPanel() {
  const element = document.createElement("section");
  element.className = "avatar-panel";
  element.innerHTML = `
    <div class="avatar-source-controls">
      <div class="avatar-source-heading">
        <p class="eyebrow">D - Avatar Source</p>
        <span class="chip" data-role="avatar-source-chip">Portrait fallback</span>
      </div>
      <div class="avatar-source-row">
        <input
          class="avatar-source-input"
          data-role="avatar-source-input"
          type="text"
          placeholder="Paste UE URL (media URL or Pixel Streaming page URL)"
        />
        <button type="button" class="secondary-button avatar-source-button" data-role="avatar-source-connect">
          Connect
        </button>
        <button type="button" class="secondary-button avatar-source-button" data-role="avatar-source-disconnect">
          Disconnect
        </button>
      </div>
      <p class="avatar-source-meta" data-role="avatar-source-meta">
        Using portrait fallback. Connect a UE URL to show the real digital human.
      </p>
    </div>
    <div class="avatar-stage avatar-stage--portrait-only">
      <div
        class="avatar-face avatar-face--portrait"
        data-expression="neutral"
        data-motion="steady"
        data-viseme="sil"
        data-gesture="none"
        data-motion-strength="1.00"
        data-emotion-style="supportive"
      >
        <div class="avatar-halo"></div>
        <div class="avatar-portrait-shell">
          <img
            class="avatar-portrait-image"
            src="./avatar-portrait.png"
            alt="Digital human portrait"
          />
          <video
            class="avatar-video hidden"
            muted
            playsinline
            autoplay
          ></video>
          <iframe
            class="avatar-embed-frame hidden"
            data-role="avatar-embed-frame"
            title="External avatar stream"
            allow="autoplay; fullscreen; camera; microphone; clipboard-read; clipboard-write"
            referrerpolicy="no-referrer"
          ></iframe>
          <div class="avatar-gesture-overlay" aria-hidden="true">
            <span class="gesture-orb gesture-orb-left"></span>
            <span class="gesture-orb gesture-orb-right"></span>
          </div>
        </div>
      </div>
    </div>
  `;

  const face = element.querySelector(".avatar-face");
  const streamInput = element.querySelector('[data-role="avatar-source-input"]');
  const connectButton = element.querySelector('[data-role="avatar-source-connect"]');
  const disconnectButton = element.querySelector('[data-role="avatar-source-disconnect"]');
  const sourceChip = element.querySelector('[data-role="avatar-source-chip"]');
  const sourceMeta = element.querySelector('[data-role="avatar-source-meta"]');
  const avatarVideo = element.querySelector(".avatar-video");
  const embedFrame = element.querySelector('[data-role="avatar-embed-frame"]');

  const renderer = createAvatarRenderer({
    faceElement: face,
    readouts: null,
  });

  face.dataset.externalPage = "off";

  function setSourceUi({ chipText, metaText, connected }) {
    sourceChip.textContent = chipText;
    sourceMeta.textContent = metaText;
    connectButton.disabled = connected;
    disconnectButton.disabled = !connected;
  }

  function setEmbedFrame(url) {
    const safeUrl = normalizeStreamUrl(url);
    if (!embedFrame) {
      return;
    }
    if (!safeUrl) {
      embedFrame.classList.add("hidden");
      embedFrame.removeAttribute("src");
      return;
    }
    embedFrame.classList.remove("hidden");
    embedFrame.src = safeUrl;
  }

  function connectExternalStream(rawUrl) {
    const url = normalizeStreamUrl(rawUrl);
    if (!url) {
      setSourceUi({
        chipText: "Portrait fallback",
        metaText: "Please provide a non-empty URL before connecting.",
        connected: false,
      });
      return false;
    }

    if (isLikelyMediaUrl(url)) {
      face.dataset.externalPage = "off";
      setEmbedFrame("");
      const applied = renderer.setPinnedVideoSource(url);
      if (!applied) {
        setSourceUi({
          chipText: "Portrait fallback",
          metaText: "Failed to bind the media URL. Check format and try again.",
          connected: false,
        });
        return false;
      }

      streamInput.value = url;
      persistStreamUrl(url);
      setSourceUi({
        chipText: "External media",
        metaText: `Connecting media stream: ${url}`,
        connected: true,
      });
      return true;
    }

    renderer.clearPinnedVideoSource();
    face.dataset.externalPage = "on";
    setEmbedFrame(url);
    streamInput.value = url;
    persistStreamUrl(url);
    setSourceUi({
      chipText: "External page",
      metaText: `Embedding external page: ${url}`,
      connected: true,
    });
    return true;
  }

  function disconnectExternalStream(message = "External source disconnected. Switched back to portrait fallback.") {
    renderer.clearPinnedVideoSource();
    face.dataset.externalPage = "off";
    setEmbedFrame("");
    persistStreamUrl("");
    setSourceUi({
      chipText: "Portrait fallback",
      metaText: message,
      connected: false,
    });
  }

  connectButton.addEventListener("click", () => {
    connectExternalStream(streamInput.value);
  });

  disconnectButton.addEventListener("click", () => {
    disconnectExternalStream();
  });

  streamInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    connectExternalStream(streamInput.value);
  });

  avatarVideo?.addEventListener("loadeddata", () => {
    if (!renderer.hasPinnedVideoSource()) {
      return;
    }
    const activeUrl = renderer.getPinnedVideoSource();
    setSourceUi({
      chipText: "External media",
      metaText: `External media stream connected: ${activeUrl}`,
      connected: true,
    });
  });

  avatarVideo?.addEventListener("error", () => {
    if (!renderer.hasPinnedVideoSource()) {
      return;
    }
    const activeUrl = renderer.getPinnedVideoSource();
    setSourceUi({
      chipText: "External media error",
      metaText: `Failed to load ${activeUrl}. Check CORS/URL and stream availability.`,
      connected: true,
    });
  });

  embedFrame?.addEventListener("load", () => {
    if (face.dataset.externalPage !== "on") {
      return;
    }
    const activeUrl = normalizeStreamUrl(streamInput.value);
    setSourceUi({
      chipText: "External page",
      metaText: `External page loaded: ${activeUrl}`,
      connected: true,
    });
  });

  embedFrame?.addEventListener("error", () => {
    if (face.dataset.externalPage !== "on") {
      return;
    }
    const activeUrl = normalizeStreamUrl(streamInput.value);
    setSourceUi({
      chipText: "External page error",
      metaText: `Failed to load ${activeUrl}. Try opening this URL in a new tab first.`,
      connected: true,
    });
  });

  setSourceUi({
    chipText: "Portrait fallback",
    metaText: "Using portrait fallback. Connect a UE URL to show the real digital human.",
    connected: false,
  });

  const initialUrl = readInitialStreamUrl();
  if (initialUrl) {
    streamInput.value = initialUrl;
    connectExternalStream(initialUrl);
  }

  const api = {
    element,
    currentEmotionStyle: "supportive",
    currentFacialExpression: "neutral",
    currentHeadMotion: "steady",
    update(response) {
      api.currentEmotionStyle = response.emotion_style || api.currentEmotionStyle;
      api.currentFacialExpression = response.avatar_action?.facial_expression || api.currentFacialExpression;
      api.currentHeadMotion = response.avatar_action?.head_motion || api.currentHeadMotion;
      renderer.render(response);
    },
  };

  return api;
}
