import { createAudioPlayer } from "./audioPlayer";
import { applyExpressionSequence } from "./expressionDriver";
import { applyMotionSequence } from "./motionDriver";
import { applyVisemeSequence } from "./visemeDriver";

export function createAvatarRenderer({ faceElement, readouts }) {
  const audioPlayer = createAudioPlayer();
  const portraitImage = faceElement.querySelector(".avatar-portrait-image");
  const videoElement = faceElement.querySelector(".avatar-video");
  let stopExpression = () => {};
  let stopMotion = () => {};
  let stopViseme = () => {};

  function cleanup() {
    stopExpression();
    stopMotion();
    stopViseme();
    audioPlayer.stop();
    if (videoElement) {
      videoElement.pause();
      videoElement.removeAttribute("src");
      videoElement.load();
      videoElement.classList.add("hidden");
    }
    if (portraitImage) {
      portraitImage.classList.remove("hidden");
    }
  }

  return {
    render(response) {
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
      audioPlayer.play(avatarOutput?.audio);

      if (videoElement && response.reply_video_url) {
        videoElement.src = response.reply_video_url;
        videoElement.classList.remove("hidden");
        portraitImage?.classList.add("hidden");
        void videoElement.play().catch(() => {
          videoElement.classList.add("hidden");
          portraitImage?.classList.remove("hidden");
        });
      }
    },
    cleanup,
  };
}
