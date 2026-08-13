export function createCameraPanel() {
  const element = document.createElement("section");
  element.className = "camera-panel";
  element.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">C · 摄像头</p>
        <h2>摄像头预览</h2>
      </div>
      <span class="chip">未启用</span>
    </div>
    <div class="camera-placeholder">
      <div class="camera-lens"></div>
      <p>摄像头未开启</p>
      <span>开启摄像头后，系统可在本轮对话中附带关键画面。</span>
    </div>
  `;
  return { element };
}
