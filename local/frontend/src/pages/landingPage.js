const FEATURE_ITEMS = [
  {
    title: "有温度",
    text: "融合文字、语音和视觉等多模态信息，感知用户当前表达与情绪状态，让陪伴不只停留在文字问答。",
  },
  {
    title: "有专业度",
    text: "结合大语言模型、心理知识库和陪护策略，提供具有知识增强和安全边界的支持性交流。",
  },
  {
    title: "有持续性",
    text: "面向多轮上下文、用户状态和长期交互记录设计，让系统从一次问答走向连续陪伴。",
  },
];

const SCENARIO_ITEMS = [
  {
    title: "居家养老",
    text: "为独居或居家老人提供日常问候、情绪倾听和陪伴式交流入口。",
  },
  {
    title: "社区养老",
    text: "辅助社区服务人员了解老人近期状态，形成更连续的关怀触点。",
  },
  {
    title: "养老机构",
    text: "为机构场景提供可演示、可扩展的数字人陪护交互原型。",
  },
];

export function renderLandingPage({ root = document.getElementById("app"), notFoundPath = "" } = {}) {
  if (!root) {
    return;
  }

  root.innerHTML = `
    <div class="landing-shell">
      <header class="landing-nav">
        <a class="brand-mark" href="/" aria-label="知心伴行首页">
          <span class="brand-symbol">心</span>
          <span>知心伴行</span>
        </a>
        <nav class="landing-nav-links" aria-label="首页导航">
          <a href="#features">产品特点</a>
          <a href="#scenarios">应用场景</a>
          <a href="#preview">产品展示</a>
          <a class="nav-cta" href="/app">开始体验</a>
        </nav>
      </header>

      ${notFoundPath ? `<section class="notice-strip">未找到 ${escapeHtml(notFoundPath)}，已为你回到产品首页。</section>` : ""}

      <main>
        <section class="landing-hero">
          <div class="hero-copy">
            <p class="eyebrow">AI 情感陪护虚拟数字人系统</p>
            <h1>知心伴行</h1>
            <p class="hero-lede">让陪伴更有温度、更专业、更持续，为老年情感陪护场景提供可体验的 AI 数字人原型。</p>
            <div class="hero-actions">
              <a class="primary-button landing-button" href="/app">开始体验</a>
              <a class="secondary-button landing-button" href="#features">查看产品特点</a>
            </div>
          </div>
          <div class="hero-product" aria-label="知心伴行产品预览">
            <div class="preview-window">
              <div class="preview-toolbar">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div class="preview-content">
                <div class="preview-avatar">
                  <img src="/avatar-portrait-idle.jpg" alt="知心伴行数字人预览" />
                </div>
                <div class="preview-dialogue">
                  <p class="preview-kicker">AI 陪护对话</p>
                  <div class="preview-bubble preview-bubble-user">最近晚上总是睡不好。</div>
                  <div class="preview-bubble preview-bubble-ai">我在这里陪你。我们可以先从今晚让身体慢慢放松开始。</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="landing-section" id="features">
          <div class="section-heading">
            <p class="eyebrow">Product Features</p>
            <h2>从问答走向陪伴</h2>
          </div>
          <div class="feature-grid">
            ${FEATURE_ITEMS.map((item) => `
              <article class="landing-card">
                <h3>${item.title}</h3>
                <p>${item.text}</p>
              </article>
            `).join("")}
          </div>
        </section>

        <section class="landing-section" id="scenarios">
          <div class="section-heading">
            <p class="eyebrow">Care Scenarios</p>
            <h2>围绕老年情感陪护场景设计</h2>
          </div>
          <div class="scenario-list">
            ${SCENARIO_ITEMS.map((item) => `
              <article class="scenario-item">
                <h3>${item.title}</h3>
                <p>${item.text}</p>
              </article>
            `).join("")}
          </div>
        </section>

        <section class="landing-section preview-section" id="preview">
          <div class="section-heading">
            <p class="eyebrow">Product Preview</p>
            <h2>产品展示</h2>
          </div>
          <div class="product-preview">
            <div>
              <h3>数字人陪护体验</h3>
              <p>体验页保留当前比赛系统的文字输入、语音输入、摄像头视觉输入、数字人切换和同步视频播放链路。</p>
            </div>
            <a class="primary-button landing-button" href="/app">进入体验</a>
          </div>
        </section>
      </main>

      <footer class="landing-footer">
        <strong>知心伴行</strong>
        <span>AI 情感陪护虚拟数字人系统</span>
      </footer>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
