export function createCameraPanel() {
  const element = document.createElement("section");
  element.className = "camera-panel";
  element.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">C · Camera</p>
        <h2>Camera Preview</h2>
      </div>
      <span class="chip">Disabled</span>
    </div>
    <div class="camera-placeholder">
      <div class="camera-lens"></div>
      <p>Camera is off</p>
      <span>Enable the camera to include key frames in this conversation turn.</span>
    </div>
  `;
  return { element };
}
