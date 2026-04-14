import { createAvatarRenderer } from "../avatar/renderer";

export function createAvatarPanel() {
  const element = document.createElement("section");
  element.className = "avatar-panel";
  element.innerHTML = `
    <div class="avatar-stage avatar-stage--portrait-only">
      <div class="avatar-face avatar-face--portrait" data-expression="neutral" data-motion="steady" data-viseme="sil">
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
        </div>
      </div>
    </div>
  `;

  const face = element.querySelector(".avatar-face");
  const renderer = createAvatarRenderer({
    faceElement: face,
    readouts: null,
  });

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
