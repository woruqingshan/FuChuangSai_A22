export function createStatusBar() {
  const element = document.createElement("section");
  element.className = "status-panel";
  element.dataset.expanded = "false";
  element.innerHTML = `
    <div class="status-summary">
      <div class="status-summary-main">
        <span class="status-dot" data-role="status-dot"></span>
        <div>
          <p class="status-summary-title" data-role="status-summary-title">AI 服务等待连接</p>
          <p class="status-summary-meta" data-role="status-summary-meta">多模态就绪</p>
        </div>
      </div>
      <button type="button" class="status-toggle-button" data-role="status-toggle" aria-expanded="false">
        详情⌄
      </button>
    </div>
    <div class="status-scroll-shell" data-role="status-details">
      <div class="panel-heading status-details-heading">
        <div>
          <p class="eyebrow">A · 状态</p>
          <h2>服务与交互状态</h2>
        </div>
        <span class="chip">会话隔离</span>
      </div>
      <dl class="status-grid">
        <div><dt>会话</dt><dd data-role="session-id"></dd></div>
        <div><dt>通道</dt><dd data-role="stream-id"></dd></div>
        <div><dt>轮次</dt><dd data-role="next-turn"></dd></div>
        <div><dt>请求</dt><dd data-role="transport"></dd></div>
        <div><dt>AI 服务</dt><dd data-role="remote-status"></dd></div>
        <div><dt>输入方式</dt><dd data-role="input-mode"></dd></div>
        <div><dt>情绪风格</dt><dd data-role="emotion-style"></dd></div>
        <div><dt>表情</dt><dd data-role="facial-expression"></dd></div>
        <div><dt>动作</dt><dd data-role="head-motion"></dd></div>
        <div><dt>语音</dt><dd data-role="audio-status"></dd></div>
        <div><dt>视觉</dt><dd data-role="video-status"></dd></div>
      </dl>
    </div>
  `;

  const refs = {
    statusDot: element.querySelector('[data-role="status-dot"]'),
    summaryTitle: element.querySelector('[data-role="status-summary-title"]'),
    summaryMeta: element.querySelector('[data-role="status-summary-meta"]'),
    toggleButton: element.querySelector('[data-role="status-toggle"]'),
    sessionId: element.querySelector('[data-role="session-id"]'),
    streamId: element.querySelector('[data-role="stream-id"]'),
    nextTurnId: element.querySelector('[data-role="next-turn"]'),
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
    refs.toggleButton.textContent = expanded ? "收起⌃" : "详情⌄";
    refs.toggleButton.setAttribute("aria-expanded", expanded ? "true" : "false");
  });

  return {
    element,
    update(snapshot) {
      const remoteStatus = snapshot.remoteStatus || "AI 服务等待连接";
      const serviceReady = /已连接|正常|就绪|ready|ok/i.test(remoteStatus);
      refs.statusDot.dataset.state = serviceReady ? "ok" : "pending";
      refs.summaryTitle.textContent = serviceReady ? "AI 服务正常" : remoteStatus;
      refs.summaryMeta.textContent = `${snapshot.transport || "等待首次对话"} · ${snapshot.inputMode || "text"}`;
      refs.sessionId.textContent = snapshot.sessionId;
      refs.streamId.textContent = snapshot.streamId;
      refs.nextTurnId.textContent = snapshot.nextTurnId;
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
