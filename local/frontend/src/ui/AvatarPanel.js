import { createAvatarRenderer } from "../avatar/renderer";

const STREAM_URL_STORAGE_KEY = "a22.avatar.external_stream_url";
const AVATAR_PROFILE_STORAGE_KEY = "a22.avatar.profile_id";
const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);

function normalizeStreamUrl(raw) {
  return String(raw || "").trim();
}

function readBooleanFlag(rawValue) {
  return TRUE_VALUES.has(String(rawValue || "").trim().toLowerCase());
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

function readInitialAvatarProfileId() {
  try {
    const queryProfileId = new URLSearchParams(window.location.search).get("avatar_profile_id");
    if (queryProfileId) {
      return String(queryProfileId).trim();
    }
  } catch {
    // Ignore malformed query string and keep fallback behavior.
  }

  try {
    return String(localStorage.getItem(AVATAR_PROFILE_STORAGE_KEY) || "").trim();
  } catch {
    return "";
  }
}

function persistAvatarProfileId(profileId) {
  try {
    if (profileId) {
      localStorage.setItem(AVATAR_PROFILE_STORAGE_KEY, profileId);
      return;
    }
    localStorage.removeItem(AVATAR_PROFILE_STORAGE_KEY);
  } catch {
    // Ignore storage failures in private mode / restricted environments.
  }
}

function readSourceControlsEnabled() {
  const envValue = import.meta.env.VITE_SHOW_AVATAR_SOURCE_CONTROLS;
  if (readBooleanFlag(envValue)) {
    return true;
  }

  try {
    const queryValue = new URLSearchParams(window.location.search).get("avatar_source_controls");
    return readBooleanFlag(queryValue);
  } catch {
    return false;
  }
}

function readDefaultPortraitUrl() {
  const envUrl = String(import.meta.env.VITE_AVATAR_PORTRAIT_URL || "").trim();
  if (envUrl) {
    return envUrl;
  }
  // Keep the idle portrait aligned with avatar A's LiveAvatar reference image.
  return "./avatar-portrait-idle.jpg?v=20260815-hands-resting";
}

function readAvatarProfiles(defaultPortraitUrl) {
  const defaultProfileId = String(import.meta.env.VITE_AVATAR_PROFILE_DEFAULT_ID || "avatar_a").trim() || "avatar_a";
  const defaultProfileName = String(import.meta.env.VITE_AVATAR_PROFILE_DEFAULT_NAME || "数字人 A").trim()
    || "数字人 A";

  const altProfileId = String(import.meta.env.VITE_AVATAR_PROFILE_ALT_ID || "avatar_b").trim() || "avatar_b";
  const altProfileName = String(import.meta.env.VITE_AVATAR_PROFILE_ALT_NAME || "数字人 B").trim()
    || "数字人 B";
  const altPortraitUrl = String(
    import.meta.env.VITE_AVATAR_PROFILE_ALT_PORTRAIT_URL || "./avatar-portrait-alt.jpg?v=20260815-casual",
  ).trim();

  const profiles = [
    { id: defaultProfileId, name: defaultProfileName, portraitUrl: defaultPortraitUrl },
  ];

  if (altProfileId && altProfileId !== defaultProfileId && altPortraitUrl) {
    profiles.push({ id: altProfileId, name: altProfileName, portraitUrl: altPortraitUrl });
  }

  return profiles;
}

export function createAvatarPanel({ onProfileChange } = {}) {
  const sourceControlsEnabled = readSourceControlsEnabled();
  const defaultPortraitUrl = readDefaultPortraitUrl();
  const avatarProfiles = readAvatarProfiles(defaultPortraitUrl);
  const element = document.createElement("section");
  element.className = "avatar-panel";
  if (sourceControlsEnabled) {
    element.classList.add("avatar-panel--show-source-controls");
  }
  element.innerHTML = `
    <div class="avatar-profile-controls">
      <div class="avatar-profile-heading">
        <p class="eyebrow">数字人形象</p>
        <span class="chip" data-role="avatar-profile-chip">待选择</span>
      </div>
      <div class="avatar-profile-row">
        <p class="avatar-profile-name" data-role="avatar-profile-name">-</p>
        <button type="button" class="secondary-button avatar-profile-button" data-role="avatar-profile-toggle">
          切换形象
        </button>
      </div>
    </div>
    <div class="avatar-source-controls">
      <div class="avatar-source-heading">
        <p class="eyebrow">D · 数字人来源</p>
        <span class="chip" data-role="avatar-source-chip">默认头像</span>
      </div>
      <div class="avatar-source-row">
        <input
          class="avatar-source-input"
          data-role="avatar-source-input"
          type="text"
          placeholder="粘贴外部数字人页面或视频地址"
        />
        <button type="button" class="secondary-button avatar-source-button" data-role="avatar-source-connect">
          连接
        </button>
        <button type="button" class="secondary-button avatar-source-button" data-role="avatar-source-disconnect">
          断开
        </button>
      </div>
      <p class="avatar-source-meta" data-role="avatar-source-meta">
        当前使用默认头像。如需外部数字人，可在这里连接页面或视频地址。
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
            src="${defaultPortraitUrl}"
            data-profile-src="${defaultPortraitUrl}"
            alt="数字人头像"
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
            title="外部数字人画面"
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
  const profileChip = element.querySelector('[data-role="avatar-profile-chip"]');
  const profileName = element.querySelector('[data-role="avatar-profile-name"]');
  const profileToggleButton = element.querySelector('[data-role="avatar-profile-toggle"]');
  const portraitImage = element.querySelector(".avatar-portrait-image");
  const avatarVideo = element.querySelector(".avatar-video");
  const embedFrame = element.querySelector('[data-role="avatar-embed-frame"]');

  const renderer = createAvatarRenderer({
    faceElement: face,
    readouts: null,
  });

  let selectedAvatarProfile = avatarProfiles[0] || {
    id: "avatar_a",
    name: "数字人 A",
    portraitUrl: defaultPortraitUrl,
  };

  face.dataset.externalPage = "off";

  function updateProfileUi(profile) {
    if (!profile) {
      return;
    }
    profileChip.textContent = profile.id;
    profileName.textContent = profile.name;
    profileToggleButton.disabled = avatarProfiles.length <= 1;
  }

  function applyProfilePortrait(profile) {
    if (!portraitImage || !profile?.portraitUrl) {
      return;
    }
    portraitImage.dataset.profileSrc = profile.portraitUrl;
    portraitImage.src = profile.portraitUrl;
  }

  function applyAvatarProfile(profile, { persist = true, notify = true } = {}) {
    if (!profile) {
      return;
    }
    // Force portrait mode when switching profile so a previously playing reply video
    // does not keep covering the new portrait.
    renderer.cleanup();
    selectedAvatarProfile = profile;
    updateProfileUi(profile);
    applyProfilePortrait(profile);
    portraitImage?.classList.remove("hidden");

    if (persist) {
      persistAvatarProfileId(profile.id);
    }
    if (notify) {
      onProfileChange?.({
        id: profile.id,
        name: profile.name,
        portraitUrl: profile.portraitUrl,
      });
    }
  }

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
        chipText: "默认头像",
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
          chipText: "默认头像",
          metaText: "Failed to bind the media URL. Check format and try again.",
          connected: false,
        });
        return false;
      }

      streamInput.value = url;
      persistStreamUrl(url);
      setSourceUi({
        chipText: "外部视频",
        metaText: `连接ing media stream: ${url}`,
        connected: true,
      });
      return true;
    }

    renderer.clearPinnedVideoSource();
    face.dataset.externalPage = "on";
    setEmbedFrame(url);
    if (streamInput) {
      streamInput.value = url;
    }
    persistStreamUrl(url);
    setSourceUi({
      chipText: "外部页面",
      metaText: `正在加载外部页面：${url}`,
      connected: true,
    });
    return true;
  }

  function disconnectExternalStream(message = "外部来源已断开，已切回默认头像。") {
    renderer.clearPinnedVideoSource();
    face.dataset.externalPage = "off";
    setEmbedFrame("");
    persistStreamUrl("");
    setSourceUi({
      chipText: "默认头像",
      metaText: message,
      connected: false,
    });
  }

  profileToggleButton.addEventListener("click", () => {
    if (avatarProfiles.length <= 1) {
      return;
    }
    const currentIndex = avatarProfiles.findIndex((item) => item.id === selectedAvatarProfile.id);
    const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % avatarProfiles.length : 0;
    const nextProfile = avatarProfiles[nextIndex];
    applyAvatarProfile(nextProfile);
  });

  portraitImage?.addEventListener("error", () => {
    if (!selectedAvatarProfile) {
      return;
    }
    if (selectedAvatarProfile.portraitUrl === defaultPortraitUrl) {
      return;
    }
    applyProfilePortrait({ portraitUrl: defaultPortraitUrl });
    setSourceUi({
      chipText: "默认头像",
      metaText: `Failed to load ${selectedAvatarProfile.portraitUrl}. Fallback portrait is used.`,
      connected: false,
    });
  });

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
      chipText: "外部视频",
      metaText: `外部视频 stream connected: ${activeUrl}`,
      connected: true,
    });
  });

  avatarVideo?.addEventListener("error", () => {
    if (!renderer.hasPinnedVideoSource()) {
      return;
    }
    const activeUrl = renderer.getPinnedVideoSource();
    setSourceUi({
      chipText: "外部视频 error",
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
      chipText: "外部页面",
      metaText: `外部页面 loaded: ${activeUrl}`,
      connected: true,
    });
  });

  embedFrame?.addEventListener("error", () => {
    if (face.dataset.externalPage !== "on") {
      return;
    }
    const activeUrl = normalizeStreamUrl(streamInput.value);
    setSourceUi({
      chipText: "外部页面 error",
      metaText: `Failed to load ${activeUrl}. Try opening this URL in a new tab first.`,
      connected: true,
    });
  });

  setSourceUi({
    chipText: "默认头像",
    metaText: "当前使用默认头像。如需外部数字人，可在这里连接页面或视频地址。",
    connected: false,
  });
  const initialProfileId = readInitialAvatarProfileId();
  const initialProfile = avatarProfiles.find((item) => item.id === initialProfileId) || avatarProfiles[0];
  applyAvatarProfile(initialProfile, { persist: false, notify: true });

  const initialUrl = readInitialStreamUrl();
  if (sourceControlsEnabled && initialUrl) {
    if (streamInput) {
      streamInput.value = initialUrl;
    }
    connectExternalStream(initialUrl);
  }
  if (!sourceControlsEnabled) {
    disconnectExternalStream("已切回默认头像。");
  }

  const api = {
    element,
    currentEmotionStyle: "supportive",
    currentFacialExpression: "neutral",
    currentHeadMotion: "steady",
    getSelectedProfileId() {
      return selectedAvatarProfile?.id || avatarProfiles[0]?.id || "avatar_a";
    },
    update(response) {
      api.currentEmotionStyle = response.emotion_style || api.currentEmotionStyle;
      api.currentFacialExpression = response.avatar_action?.facial_expression || api.currentFacialExpression;
      api.currentHeadMotion = response.avatar_action?.head_motion || api.currentHeadMotion;
      return renderer.render(response);
    },
  };

  return api;
}
