import { createAudioPlayer } from "./audioPlayer";
import { applyExpressionSequence } from "./expressionDriver";
import { applyMotionSequence } from "./motionDriver";
import { applyVisemeSequence } from "./visemeDriver";

export function createAvatarRenderer({ faceElement, readouts }) {
  const audioPlayer = createAudioPlayer();
  const portraitImage = faceElement.querySelector(".avatar-portrait-image");
  const videoElement = faceElement.querySelector(".avatar-video");
  const portraitDefaultSrc = portraitImage?.getAttribute("src") || "";
  let stopExpression = () => {};
  let stopMotion = () => {};
  let stopViseme = () => {};
  let renderToken = 0;
  let detachVideoListeners = () => {};

  function freezeCurrentVideoFrame() {
    if (!portraitImage || !videoElement) {
      return;
    }
    if (videoElement.classList.contains("hidden")) {
      if (portraitDefaultSrc && !portraitImage.getAttribute("src")) {
        portraitImage.setAttribute("src", portraitDefaultSrc);
      }
      return;
    }
    const width = videoElement.videoWidth;
    const height = videoElement.videoHeight;
    if (!width || !height) {
      return;
    }
    try {
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d");
      if (!context) {
        return;
      }
      context.drawImage(videoElement, 0, 0, width, height);
      portraitImage.setAttribute("src", canvas.toDataURL("image/jpeg", 0.92));
    } catch {
      if (portraitDefaultSrc) {
        portraitImage.setAttribute("src", portraitDefaultSrc);
      }
    }
  }

  function resetVideoElement() {
    if (!videoElement) {
      return;
    }
    detachVideoListeners();
    videoElement.pause();
    videoElement.currentTime = 0;
    videoElement.removeAttribute("src");
    videoElement.load();
    videoElement.classList.add("hidden");
  }

  function cleanup() {
    renderToken += 1;
    stopExpression();
    stopMotion();
    stopViseme();
    audioPlayer.stop();
    freezeCurrentVideoFrame();
    resetVideoElement();
    if (portraitImage) {
      portraitImage.classList.remove("hidden");
    }
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
      portraitImage?.classList.add("hidden");
    };

    const handleReady = () => {
      cleanupListeners();
      revealVideo();
      void videoElement.play().catch(() => {
        if (renderToken !== currentToken) {
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

    const cleanupListeners = () => {
      videoElement.removeEventListener("loadeddata", handleReady);
      videoElement.removeEventListener("canplay", handleReady);
      videoElement.removeEventListener("error", handleError);
      detachVideoListeners = () => {};
    };

    detachVideoListeners = cleanupListeners;
    videoElement.addEventListener("loadeddata", handleReady, { once: true });
    videoElement.addEventListener("canplay", handleReady, { once: true });
    videoElement.addEventListener("error", handleError, { once: true });
  }

  return {
    render(response) {
      const currentToken = renderToken + 1;
      cleanup();

      const fallbackExpression = response.avatar_action?.facial_expression || "neutral";
      const fallbackMotion = response.avatar_action?.head_motion || "steady";
      const avatarOutput = response.avatar_output;

      const emotionStyle = avatarOutput?.emotion_style || response.emotion_style || "supportive";
      const expressionSeq = avatarOutput?.expression_seq || [];
      const motionSeq = avatarOutput?.motion_seq || [];
      const visemeSeq = avatarOutput?.viseme_seq || [];

      if (readouts) {
        readouts.emotionStyle.textContent = emotionStyle;
        readouts.facialExpression.textContent = expressionSeq[0]?.expression || fallbackExpression;
        readouts.headMotion.textContent = motionSeq[0]?.motion || fallbackMotion;
      }

      stopExpression = applyExpressionSequence(faceElement, expressionSeq, fallbackExpression);
      stopMotion = applyMotionSequence(faceElement, motionSeq, fallbackMotion);
      stopViseme = applyVisemeSequence(faceElement, visemeSeq);

      if (videoElement && response.reply_video_url) {
        renderToken = currentToken;
        videoElement.muted = false;
        videoElement.playsInline = true;
        videoElement.loop = false;
        videoElement.preload = "auto";
        videoElement.currentTime = 0;
        videoElement.classList.add("hidden");
        portraitImage?.classList.remove("hidden");
        armVideoTransition(currentToken);
        videoElement.src = response.reply_video_url;
        videoElement.load();
        return;
      }

      audioPlayer.play(avatarOutput?.audio);
    },
    cleanup,
  };
}
