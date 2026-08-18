import { createAudioPlayer } from "./audioPlayer";
import { applyExpressionSequence } from "./expressionDriver";
import { applyMotionSequence } from "./motionDriver";
import { applyVisemeSequence } from "./visemeDriver";

function resolveBackendMediaUrl(rawUrl) {
  const url = String(rawUrl || "").trim();
  if (!url) {
    return "";
  }

  const lower = url.toLowerCase();
  if (lower.startsWith("http://") || lower.startsWith("https://") || lower.startsWith("data:") || lower.startsWith("blob:")) {
    return url;
  }

  const directApiEnabled = import.meta.env.VITE_USE_DIRECT_API === "true";
  const directApiBase = directApiEnabled
    ? String(import.meta.env.VITE_API_BASE || "").trim().replace(/\/$/, "")
    : "";
  if (!directApiBase) {
    return url;
  }

  if (url.startsWith("/")) {
    return `${directApiBase}${url}`;
  }
  return `${directApiBase}/${url}`;
}

async function resolveStreamFirstChunkUrl(streamManifestUrl) {
  const startedAt = Date.now();
  const configuredTimeout = Number(import.meta.env.VITE_AVATAR_VIDEO_WAIT_TIMEOUT_MS || 1800000);
  const timeoutMs = Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 1800000;
  const pollIntervalMs = 1000;

  while (Date.now() - startedAt <= timeoutMs) {
    const manifestResponse = await fetch(streamManifestUrl, {
      cache: "no-store",
    }).catch(() => null);
    if (!manifestResponse || !manifestResponse.ok) {
      if (manifestResponse?.status === 401) {
        throw new Error("会话已失效，请重新开始");
      }
      if (manifestResponse?.status === 403) {
        throw new Error("当前媒体不属于此会话");
      }
      await waitFor(pollIntervalMs);
      continue;
    }

    const manifest = await manifestResponse.json().catch(() => null);
    const chunks = Array.isArray(manifest?.chunks) ? manifest.chunks : [];
    if (chunks.length) {
      const firstChunkUrl = typeof chunks[0]?.url === "string" ? chunks[0].url : "";
      return resolveBackendMediaUrl(firstChunkUrl);
    }
    if (manifest?.complete) {
      throw new Error(manifest?.error || "数字人视频生成失败");
    }
    await waitFor(pollIntervalMs);
  }

  throw new Error("数字人视频生成等待超时");
}

function waitFor(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

const VIDEO_FADE_MS = 550;

export function createAvatarRenderer({ faceElement, readouts }) {
  const audioPlayer = createAudioPlayer();
  const portraitImage = faceElement.querySelector(".avatar-portrait-image");
  const videoElement = faceElement.querySelector(".avatar-video");
  const portraitShell = faceElement.querySelector(".avatar-portrait-shell");
  const renderStatus = document.createElement("div");
  renderStatus.className = "avatar-render-status hidden";
  renderStatus.setAttribute("role", "status");
  renderStatus.setAttribute("aria-live", "polite");
  portraitShell?.appendChild(renderStatus);
  const portraitDefaultSrc = portraitImage?.getAttribute("src") || "";
  let stopExpression = () => {};
  let stopMotion = () => {};
  let stopViseme = () => {};
  let renderToken = 0;
  let detachVideoListeners = () => {};
  let pinnedVideoSource = "";

  function setRenderStatus(message = "") {
    const text = String(message || "").trim();
    renderStatus.textContent = text;
    renderStatus.classList.toggle("hidden", !text);
    faceElement.dataset.renderStatus = text ? "waiting" : "idle";
  }

  function setExternalStreamFlag(enabled) {
    faceElement.dataset.externalStream = enabled ? "on" : "off";
  }

  function restoreProfilePortrait() {
    if (!portraitImage) {
      return;
    }
    const profileSrc = portraitImage.dataset.profileSrc || portraitDefaultSrc;
    if (profileSrc) {
      portraitImage.setAttribute("src", profileSrc);
    }
  }

  function resetVideoElement({ removeSource = true } = {}) {
    if (!videoElement) {
      return;
    }
    detachVideoListeners();
    videoElement.pause();
    videoElement.currentTime = 0;
    if (removeSource) {
      videoElement.removeAttribute("src");
      videoElement.removeAttribute("data-source-url");
      videoElement.removeAttribute("data-source-type");
      videoElement.load();
    }
    videoElement.classList.remove("avatar-video--visible");
    videoElement.classList.add("hidden");
  }

  function cleanup({ preserveVideo = false } = {}) {
    renderToken += 1;
    stopExpression();
    stopMotion();
    stopViseme();
    audioPlayer.stop();
    if (!preserveVideo) {
      // Keep the currently selected portrait image stable.
      // Do not overwrite it with the previous reply video's last frame,
      // otherwise profile switching appears one-turn delayed.
      resetVideoElement();
      if (portraitImage) {
        portraitImage.classList.remove("hidden");
      }
    }
    setRenderStatus();
  }

  function armVideoTransition(currentToken) {
    if (!videoElement) {
      return;
    }

    const revealVideo = () => {
      if (renderToken !== currentToken) {
        return;
      }
      videoElement.classList.remove("hidden");
      portraitImage?.classList.remove("hidden");
      window.requestAnimationFrame(() => {
        if (renderToken === currentToken) {
          videoElement.classList.add("avatar-video--visible");
        }
      });
    };

    const handleReady = () => {
      cleanupReadyListeners();
      revealVideo();
      void videoElement.play().catch(() => {
        if (renderToken !== currentToken) {
          return;
        }
        if (!videoElement.muted) {
          videoElement.controls = true;
          revealVideo();
          setRenderStatus("视频已生成，请点击播放");
          return;
        }
        resetVideoElement();
        portraitImage?.classList.remove("hidden");
      });
    };

    const handleError = () => {
      cleanupListeners();
      if (renderToken !== currentToken) {
        return;
      }
      resetVideoElement();
      portraitImage?.classList.remove("hidden");
    };

    const handleEnded = () => {
      if (renderToken !== currentToken) {
        return;
      }
      stopExpression();
      stopMotion();
      stopViseme();
      faceElement.dataset.expression = "neutral";
      faceElement.dataset.motion = "steady";
      faceElement.dataset.gesture = "none";
      faceElement.dataset.viseme = "sil";
      restoreProfilePortrait();
      faceElement.dataset.playbackEnded = "true";
      portraitImage?.classList.remove("hidden");
      cleanupListeners();
      videoElement.classList.remove("avatar-video--visible");
      window.setTimeout(() => {
        if (renderToken === currentToken) {
          resetVideoElement();
        }
      }, VIDEO_FADE_MS);
    };

    const cleanupReadyListeners = () => {
      videoElement.removeEventListener("loadeddata", handleReady);
      videoElement.removeEventListener("canplay", handleReady);
    };

    const cleanupListeners = () => {
      cleanupReadyListeners();
      videoElement.removeEventListener("error", handleError);
      videoElement.removeEventListener("ended", handleEnded);
      detachVideoListeners = () => {};
    };

    detachVideoListeners = cleanupListeners;
    videoElement.addEventListener("loadeddata", handleReady, { once: true });
    videoElement.addEventListener("canplay", handleReady, { once: true });
    videoElement.addEventListener("error", handleError, { once: true });
    videoElement.addEventListener("ended", handleEnded, { once: true });
  }

  function startVideoSource({ url, currentToken, muted, loop, sourceType }) {
    if (!videoElement || !url) {
      return false;
    }
    renderToken = currentToken;
    faceElement.dataset.playbackEnded = "false";
    videoElement.muted = Boolean(muted);
    videoElement.controls = false;
    videoElement.playsInline = true;
    videoElement.loop = Boolean(loop);
    videoElement.preload = "auto";
    videoElement.currentTime = 0;
    videoElement.classList.remove("avatar-video--visible");
    videoElement.classList.add("hidden");
    portraitImage?.classList.remove("hidden");
    armVideoTransition(currentToken);
    videoElement.dataset.sourceUrl = url;
    videoElement.dataset.sourceType = sourceType;
    videoElement.src = url;
    videoElement.load();
    return true;
  }

  function ensurePinnedVideoPlaying(currentToken) {
    if (!videoElement || !pinnedVideoSource) {
      return false;
    }
    const currentSource = videoElement.dataset.sourceUrl || "";
    const currentType = videoElement.dataset.sourceType || "";
    const visible = !videoElement.classList.contains("hidden");
    if (visible && currentType === "external" && currentSource === pinnedVideoSource) {
      return true;
    }
    return startVideoSource({
      url: pinnedVideoSource,
      currentToken,
      muted: true,
      loop: true,
      sourceType: "external",
    });
  }

  setExternalStreamFlag(false);

  return {
    setPinnedVideoSource(url) {
      const next = String(url || "").trim();
      if (!next) {
        pinnedVideoSource = "";
        setExternalStreamFlag(false);
        cleanup();
        return false;
      }

      pinnedVideoSource = next;
      setExternalStreamFlag(true);
      const currentToken = renderToken + 1;
      cleanup();
      return startVideoSource({
        url: pinnedVideoSource,
        currentToken,
        muted: true,
        loop: true,
        sourceType: "external",
      });
    },
    clearPinnedVideoSource() {
      pinnedVideoSource = "";
      setExternalStreamFlag(false);
      cleanup();
    },
    getPinnedVideoSource() {
      return pinnedVideoSource;
    },
    hasPinnedVideoSource() {
      return Boolean(pinnedVideoSource);
    },
    async render(response) {
      const externalStreamPinned = Boolean(pinnedVideoSource);
      const currentToken = renderToken + 1;
      cleanup({ preserveVideo: externalStreamPinned });

      const fallbackExpression = response.avatar_action?.facial_expression || "neutral";
      const fallbackMotion = response.avatar_action?.head_motion || "steady";
      const avatarOutput = response.avatar_output;
      const synchronizedVideo = avatarOutput?.renderer_mode === "synchronized_video";

      const emotionStyle = avatarOutput?.emotion_style || response.emotion_style || "supportive";
      const expressionSeq = avatarOutput?.expression_seq || [];
      const motionSeq = avatarOutput?.motion_seq || [];
      const visemeSeq = avatarOutput?.viseme_seq || [];
      faceElement.dataset.emotionStyle = String(emotionStyle).toLowerCase();

      if (readouts) {
        readouts.emotionStyle.textContent = emotionStyle;
        readouts.facialExpression.textContent = expressionSeq[0]?.expression || fallbackExpression;
        readouts.headMotion.textContent = motionSeq[0]?.motion || fallbackMotion;
      }

      if (externalStreamPinned) {
        setExternalStreamFlag(true);
        stopExpression = () => {};
        stopMotion = () => {};
        stopViseme = () => {};
        ensurePinnedVideoPlaying(currentToken);
        audioPlayer.play(avatarOutput?.audio);
        return { status: "ready", synchronizedVideo: false };
      }

      setExternalStreamFlag(false);
      stopExpression = applyExpressionSequence(faceElement, expressionSeq, fallbackExpression);
      stopMotion = applyMotionSequence(faceElement, motionSeq, fallbackMotion);
      stopViseme = applyVisemeSequence(faceElement, visemeSeq);
      const audioCue = avatarOutput?.audio;
      // LiveAvatar output already contains the synchronized audio track. Other
      // renderers keep their historical reply.wav + muted-video behavior.
      if (!synchronizedVideo) {
        audioPlayer.play(audioCue);
      }

      const replyVideoUrl = resolveBackendMediaUrl(response.reply_video_url);
      if (videoElement && replyVideoUrl) {
        startVideoSource({
          url: replyVideoUrl,
          currentToken,
          muted: !synchronizedVideo,
          loop: false,
          sourceType: "reply",
        });
        return { status: "ready", synchronizedVideo };
      }

      const replyVideoStreamUrl = resolveBackendMediaUrl(response.reply_video_stream_url);
      if (videoElement && replyVideoStreamUrl) {
        if (synchronizedVideo) {
          setRenderStatus("数字人视频生成中，请稍候…");
        }
        try {
          const chunkUrl = await resolveStreamFirstChunkUrl(replyVideoStreamUrl);
          if (renderToken !== currentToken) {
            return { status: "cancelled", synchronizedVideo };
          }
          setRenderStatus();
          startVideoSource({
            url: chunkUrl,
            currentToken,
            muted: !synchronizedVideo,
            loop: false,
            sourceType: "reply",
          });
          return { status: "ready", synchronizedVideo };
        } catch (error) {
          if (renderToken === currentToken && synchronizedVideo) {
            setRenderStatus(error instanceof Error ? error.message : "数字人视频生成失败");
          }
          throw error;
        }
      }
      return { status: "ready", synchronizedVideo };
    },
    cleanup,
  };
}
