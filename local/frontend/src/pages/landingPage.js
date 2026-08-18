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

const CAROUSEL_SLIDES = [
  {
    title: "数字人 A",
    subtitle: "温和、稳定的陪护表达",
    image: "/avatar-portrait-idle.jpg",
    alt: "知心伴行数字人 A 预览",
  },
  {
    title: "数字人 B",
    subtitle: "更生活化的陪伴形象",
    image: "/avatar-portrait-alt.jpg",
    alt: "知心伴行数字人 B 预览",
  },
  {
    title: "更多形象持续开发中",
    subtitle: "More avatars coming soon",
    image: "",
    alt: "",
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
          <span class="brand-symbol" aria-hidden="true">知</span>
          <span class="brand-wordmark">知心伴行</span>
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
              <a class="text-link-button" href="#features">查看产品特点</a>
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
                <div class="avatar-carousel" data-role="avatar-carousel">
                  <div class="carousel-track" data-role="carousel-track">
                    ${CAROUSEL_SLIDES.map((slide, index) => `
                      <article class="carousel-slide${index === 0 ? " is-active" : ""}" data-slide-index="${index}">
                        ${slide.image
                          ? `<img src="${slide.image}" alt="${slide.alt}" />`
                          : `<div class="carousel-placeholder" aria-hidden="true">
                              <span>+</span>
                            </div>`}
                        <div class="carousel-caption">
                          <strong>${slide.title}</strong>
                          <span>${slide.subtitle}</span>
                        </div>
                      </article>
                    `).join("")}
                  </div>
                  <button type="button" class="carousel-arrow carousel-arrow-prev" data-role="carousel-prev" aria-label="上一张数字人形象">‹</button>
                  <button type="button" class="carousel-arrow carousel-arrow-next" data-role="carousel-next" aria-label="下一张数字人形象">›</button>
                  <div class="carousel-indicators" data-role="carousel-indicators" aria-label="数字人形象轮播指示">
                    ${CAROUSEL_SLIDES.map((_, index) => `
                      <button type="button" class="${index === 0 ? "is-active" : ""}" data-slide-target="${index}" aria-label="查看第 ${index + 1} 张"></button>
                    `).join("")}
                  </div>
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

      <div class="service-modal-backdrop" data-role="service-modal" hidden>
        <section class="service-modal" role="dialog" aria-modal="true" aria-labelledby="service-modal-title">
          <p class="eyebrow">AI Service Status</p>
          <h2 id="service-modal-title">AI 服务暂未启动</h2>
          <p>当前数字人推理服务还没有连接，请稍后再试。</p>
          <div class="service-modal-actions">
            <button type="button" class="secondary-button" data-role="service-modal-close">我知道了</button>
            <button type="button" class="primary-button landing-button" data-role="service-modal-retry">重新检查</button>
          </div>
        </section>
      </div>
    </div>
  `;

  initHeroCarousel(root);
  initExperienceGate(root);
}

function initHeroCarousel(root) {
  const carousel = root.querySelector('[data-role="avatar-carousel"]');
  if (!carousel) {
    return;
  }

  const slides = Array.from(carousel.querySelectorAll(".carousel-slide"));
  const indicators = Array.from(carousel.querySelectorAll("[data-slide-target]"));
  const prevButton = carousel.querySelector('[data-role="carousel-prev"]');
  const nextButton = carousel.querySelector('[data-role="carousel-next"]');
  let currentIndex = 0;
  let timer = null;

  function showSlide(nextIndex) {
    currentIndex = (nextIndex + slides.length) % slides.length;
    slides.forEach((slide, index) => {
      slide.classList.toggle("is-active", index === currentIndex);
    });
    indicators.forEach((indicator, index) => {
      indicator.classList.toggle("is-active", index === currentIndex);
      indicator.setAttribute("aria-current", index === currentIndex ? "true" : "false");
    });
  }

  function stopAutoPlay() {
    if (timer) {
      window.clearInterval(timer);
      timer = null;
    }
  }

  function startAutoPlay() {
    stopAutoPlay();
    timer = window.setInterval(() => showSlide(currentIndex + 1), 5000);
  }

  prevButton?.addEventListener("click", () => {
    showSlide(currentIndex - 1);
    startAutoPlay();
  });
  nextButton?.addEventListener("click", () => {
    showSlide(currentIndex + 1);
    startAutoPlay();
  });
  indicators.forEach((indicator) => {
    indicator.addEventListener("click", () => {
      showSlide(Number(indicator.dataset.slideTarget || 0));
      startAutoPlay();
    });
  });
  carousel.addEventListener("mouseenter", stopAutoPlay);
  carousel.addEventListener("mouseleave", startAutoPlay);
  showSlide(0);
  startAutoPlay();
}

function initExperienceGate(root) {
  const appLinks = Array.from(root.querySelectorAll('a[href="/app"]'));
  const modal = root.querySelector('[data-role="service-modal"]');
  const closeButton = root.querySelector('[data-role="service-modal-close"]');
  const retryButton = root.querySelector('[data-role="service-modal-retry"]');
  let targetHref = "/app";
  let checking = false;

  async function attemptEntry(sourceElement) {
    if (checking) {
      return;
    }
    checking = true;
    sourceElement?.classList.add("is-checking");
    sourceElement?.setAttribute("aria-busy", "true");
    retryButton?.classList.add("is-checking");
    retryButton?.setAttribute("aria-busy", "true");

    const available = await checkAiServiceAvailable();

    sourceElement?.classList.remove("is-checking");
    sourceElement?.removeAttribute("aria-busy");
    retryButton?.classList.remove("is-checking");
    retryButton?.removeAttribute("aria-busy");
    checking = false;

    if (available) {
      window.location.assign(targetHref);
      return;
    }
    showServiceModal(modal, closeButton);
  }

  appLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      targetHref = link.getAttribute("href") || "/app";
      attemptEntry(link);
    });
  });

  closeButton?.addEventListener("click", () => hideServiceModal(modal));
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) {
      hideServiceModal(modal);
    }
  });
  retryButton?.addEventListener("click", () => attemptEntry(retryButton));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal && !modal.hidden) {
      hideServiceModal(modal);
    }
  });
}

async function checkAiServiceAvailable() {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 3500);
  try {
    const response = await fetch("/api/status", {
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) {
      return false;
    }
    const payload = await readJsonSafely(response);
    return isAiServiceReady(payload);
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function readJsonSafely(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return {};
  }
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function isAiServiceReady(payload) {
  if (!payload || typeof payload !== "object") {
    return true;
  }

  const booleanSignals = [
    payload.ai_available,
    payload.available,
    payload.ready,
    payload.ok,
  ];
  if (booleanSignals.some((value) => value === false)) {
    return false;
  }
  if (booleanSignals.some((value) => value === true)) {
    return true;
  }

  const statusText = [
    payload.ai,
    payload.status,
    payload.ai_status,
    payload.gateway,
    payload.orchestrator,
  ]
    .filter((value) => typeof value === "string")
    .join(" ")
    .toLowerCase();

  if (/unavailable|offline|down|disconnected|failed|not connected/.test(statusText)) {
    return false;
  }
  if (/available|online|ready|healthy|connected|ok/.test(statusText)) {
    return true;
  }
  return true;
}

function showServiceModal(modal, closeButton) {
  if (!modal) {
    return;
  }
  modal.hidden = false;
  window.setTimeout(() => closeButton?.focus(), 0);
}

function hideServiceModal(modal) {
  if (modal) {
    modal.hidden = true;
  }
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
