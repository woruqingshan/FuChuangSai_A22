const FEATURE_ITEMS = [
  {
    title: "Physical Presence",
    text: "At home, an embodied companion robot interacts through voice, vision, expressive displays, and physical motion.",
  },
  {
    title: "Shared Intelligence",
    text: "Both embodiments access the same user identity, profile, long-term memory, and cloud AI services.",
  },
  {
    title: "Cross-Device Continuity",
    text: "Move between the home robot and the browser-based digital human while preserving persistent personalized context.",
  },
];

const SCENARIO_ITEMS = [
  {
    title: "At Home — Physical Robot",
    text: "The home robot provides embodied interaction through voice, vision, expression, and motion.",
  },
  {
    title: "On the Go — Web Digital Human",
    text: "Access the same companion from a smartphone or computer browser while away from home.",
  },
  {
    title: "Across Environments — Shared Context",
    text: "The same identity, profile, and long-term memory support personalized interaction across both embodiments.",
  },
];

const CAROUSEL_SLIDES = [
  {
    title: "EVA",
    subtitle: "Physical companion robot",
    image: "/physical-companion-robot.png",
    alt: "EVA physical companion robot",
  },
  {
    title: "Avatar B",
    subtitle: "Casual companion",
    image: "/avatar-portrait-alt.jpg",
    alt: "OneCompanion Avatar B preview",
  },
  {
    title: "More Avatars Coming Soon",
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
        <a class="brand-mark" href="/" aria-label="EVA OneCompanion home">
          <span class="brand-symbol" aria-hidden="true">EVA</span>
          <span class="brand-wordmark">OneCompanion</span>
        </a>
        <nav class="landing-nav-links" aria-label="Main navigation">
          <a href="#features">Features</a>
          <a href="#scenarios">How It Works</a>
          <a href="#preview">Demo</a>
          <a class="nav-cta" href="/app">Try the Demo</a>
        </nav>
      </header>

      ${notFoundPath ? `<section class="notice-strip">Page ${escapeHtml(notFoundPath)} was not found. You have been returned to the product home page.</section>` : ""}

      <main>
        <section class="landing-hero">
          <div class="hero-copy">
            <div class="hero-heading-panel">
              <div class="hero-heading-copy">
                <p class="eyebrow">CROSS-DEVICE AI COMPANION</p>
                <h1>EVA: <span class="hero-eva-initial">E</span>mpatía para la <span class="hero-eva-initial">V</span>ida, <span class="hero-eva-initial">A</span>compañante en cada momento.</h1>
              </div>
              <figure class="hero-robot-proof">
                <img src="/physical-companion-robot.png" alt="EVA physical companion robot" />
              </figure>
            </div>
            <p class="hero-lede">EVA: your personal AI-powered companion, navigating life’s experiences alongside you.</p>
            <div class="hero-actions">
              <a class="primary-button landing-button" href="/app">Try the Demo</a>
              <a class="text-link-button" href="#features">Explore Features</a>
            </div>
          </div>
          <div class="hero-product" aria-label="OneCompanion product preview">
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
                  <button type="button" class="carousel-arrow carousel-arrow-prev" data-role="carousel-prev" aria-label="Previous Avatar">‹</button>
                  <button type="button" class="carousel-arrow carousel-arrow-next" data-role="carousel-next" aria-label="Next Avatar">›</button>
                  <div class="carousel-indicators" data-role="carousel-indicators" aria-label="Avatar Carousel">
                    ${CAROUSEL_SLIDES.map((_, index) => `
                      <button type="button" class="${index === 0 ? "is-active" : ""}" data-slide-target="${index}" aria-label="View Avatar ${index + 1}"></button>
                    `).join("")}
                  </div>
                </div>
                <div class="preview-dialogue">
                  <p class="preview-kicker">AI Companion</p>
                  <div class="preview-bubble preview-bubble-user">I have an important appointment this afternoon.</div>
                  <div class="preview-bubble preview-bubble-ai">I'll remember that. You can continue our conversation later from another device.</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="landing-section" id="features">
          <div class="section-heading">
            <p class="eyebrow">Product Features</p>
            <h2>From a Single Device to a Continuous Companion</h2>
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
            <p class="eyebrow">How It Works</p>
            <h2>One Companion Across Daily Life</h2>
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
            <p class="eyebrow">Demo</p>
            <h2>Experience OneCompanion</h2>
          </div>
          <div class="product-preview">
            <div>
              <h3>Digital Companion Experience</h3>
              <p>The demo supports text, voice, and optional camera input, avatar switching, personalized AI responses, and synchronized digital-human playback.</p>
            </div>
            <a class="primary-button landing-button" href="/app">Launch Demo</a>
          </div>
        </section>
      </main>

      <footer class="landing-footer">
        <strong>OneCompanion</strong>
        <span>Cross-Device AI Companion</span>
      </footer>

      <div class="service-modal-backdrop" data-role="service-modal" hidden>
        <section class="service-modal" role="dialog" aria-modal="true" aria-labelledby="service-modal-title">
          <p class="eyebrow">AI Service Status</p>
          <h2 id="service-modal-title">AI Service Unavailable</h2>
          <p>The AI companion service is not connected at the moment. Please try again shortly.</p>
          <div class="service-modal-actions">
            <button type="button" class="secondary-button" data-role="service-modal-close">Close</button>
            <button type="button" class="primary-button landing-button" data-role="service-modal-retry">Check Again</button>
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
