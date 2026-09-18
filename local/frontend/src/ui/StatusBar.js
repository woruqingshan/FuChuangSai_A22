export function createStatusBar() {
  const element = document.createElement("section");
  element.className = "status-panel";
  element.dataset.expanded = "false";
  element.innerHTML = `
    <div class="status-summary">
      <div class="status-summary-main">
        <span class="status-dot" data-role="status-dot"></span>
        <div>
          <p class="status-summary-title" data-role="status-summary-title">Waiting for AI Service</p>
          <p class="status-summary-meta" data-role="status-summary-meta">Multimodal Ready</p>
        </div>
      </div>
      <button type="button" class="status-toggle-button" data-role="status-toggle" aria-expanded="false">
        Details⌄
      </button>
    </div>
    <div class="status-scroll-shell" data-role="status-details">
      <div class="panel-heading status-details-heading">
        <div>
          <p class="eyebrow">A · Status</p>
          <h2>Service Status</h2>
        </div>
        <span class="chip">Secure Connection</span>
      </div>
      <dl class="status-grid">
        <div><dt>Status</dt><dd data-role="transport"></dd></div>
        <div><dt>AI Service</dt><dd data-role="remote-status"></dd></div>
        <div><dt>Input Mode</dt><dd data-role="input-mode"></dd></div>
        <div><dt>Emotion Style</dt><dd data-role="emotion-style"></dd></div>
        <div><dt>Expression</dt><dd data-role="facial-expression"></dd></div>
        <div><dt>Motion</dt><dd data-role="head-motion"></dd></div>
        <div><dt>Audio</dt><dd data-role="audio-status"></dd></div>
        <div><dt>Vision</dt><dd data-role="video-status"></dd></div>
      </dl>
    </div>
  `;

  const refs = {
    statusDot: element.querySelector('[data-role="status-dot"]'),
    summaryTitle: element.querySelector('[data-role="status-summary-title"]'),
    summaryMeta: element.querySelector('[data-role="status-summary-meta"]'),
    toggleButton: element.querySelector('[data-role="status-toggle"]'),
    transport: element.querySelector('[data-role="transport"]'),
    remoteStatus: element.querySelector('[data-role="remote-status"]'),
    inputMode: element.querySelector('[data-role="input-mode"]'),
    emotionStyle: element.querySelector('[data-role="emotion-style"]'),
    facialExpression: element.querySelector('[data-role="facial-expression"]'),
    headMotion: element.querySelector('[data-role="head-motion"]'),
    audioStatus: element.querySelector('[data-role="audio-status"]'),
    videoStatus: element.querySelector('[data-role="video-status"]'),
  };

  refs.toggleButton.addEventListener("click", () => {
    const expanded = element.dataset.expanded !== "true";
    element.dataset.expanded = expanded ? "true" : "false";
    refs.toggleButton.textContent = expanded ? "Hide Details⌃" : "Details⌄";
    refs.toggleButton.setAttribute("aria-expanded", expanded ? "true" : "false");
  });

  return {
    element,
    update(snapshot) {
      const remoteStatus = snapshot.remoteStatus || "Waiting for AI Service";
      const serviceReady = /connected|ready|healthy|normal|ok/i.test(remoteStatus);
      refs.statusDot.dataset.state = serviceReady ? "ok" : "pending";
      refs.summaryTitle.textContent = serviceReady ? "AI Service Ready" : remoteStatus;
      refs.summaryMeta.textContent = `${snapshot.transport || "Waiting for First Interaction"} · ${snapshot.inputMode || "text"}`;
      refs.transport.textContent = snapshot.transport;
      refs.remoteStatus.textContent = snapshot.remoteStatus;
      refs.inputMode.textContent = snapshot.inputMode;
      refs.emotionStyle.textContent = snapshot.emotionStyle;
      refs.facialExpression.textContent = snapshot.facialExpression;
      refs.headMotion.textContent = snapshot.headMotion;
      refs.audioStatus.textContent = snapshot.audioStatus;
      refs.videoStatus.textContent = snapshot.videoStatus;
    },
  };
}
