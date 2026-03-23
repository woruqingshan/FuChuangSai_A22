export function createAvatarPanel() {
  const element = document.createElement("section");
  element.className = "avatar-panel";
  element.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">A · Avatar</p>
        <h2>Digital Human Render Panel</h2>
      </div>
      <span class="chip">2D placeholder</span>
    </div>
    <div class="avatar-stage">
      <div class="avatar-face" data-expression="neutral" data-motion="steady">
        <div class="avatar-halo"></div>
        <div class="avatar-head">
          <div class="avatar-eyes">
            <span></span>
            <span></span>
          </div>
          <div class="avatar-mouth"></div>
        </div>
      </div>
      <div class="avatar-readout">
        <div>
          <span class="readout-label">Emotion</span>
          <strong data-role="emotion-style">supportive</strong>
        </div>
        <div>
          <span class="readout-label">Expression</span>
          <strong data-role="facial-expression">neutral</strong>
        </div>
        <div>
          <span class="readout-label">Head motion</span>
          <strong data-role="head-motion">steady</strong>
        </div>
      </div>
    </div>
  `;

  const face = element.querySelector(".avatar-face");
  const emotionStyle = element.querySelector('[data-role="emotion-style"]');
  const facialExpression = element.querySelector('[data-role="facial-expression"]');
  const headMotion = element.querySelector('[data-role="head-motion"]');

  const api = {
    element,
    currentEmotionStyle: "supportive",
    currentFacialExpression: "neutral",
    currentHeadMotion: "steady",
    update(response) {
      api.currentEmotionStyle = response.emotion_style || api.currentEmotionStyle;
      api.currentFacialExpression = response.avatar_action?.facial_expression || api.currentFacialExpression;
      api.currentHeadMotion = response.avatar_action?.head_motion || api.currentHeadMotion;

      emotionStyle.textContent = api.currentEmotionStyle;
      facialExpression.textContent = api.currentFacialExpression;
      headMotion.textContent = api.currentHeadMotion;

      face.dataset.expression = api.currentFacialExpression;
      face.dataset.motion = api.currentHeadMotion;
    },
  };

  return api;
}
