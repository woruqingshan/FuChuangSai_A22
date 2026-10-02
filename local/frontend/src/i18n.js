const STORAGE_KEY = "onecompanion.ui_language";
const SUPPORTED_LANGUAGES = new Set(["en", "es"]);

const ES = {
  "Features": "Características",
  "How It Works": "Cómo funciona",
  "Demo": "Demostración",
  "Try the Demo": "Probar la demostración",
  "CROSS-DEVICE AI COMPANION": "COMPAÑERO DE IA MULTIDISPOSITIVO",
  "EVA: your personal AI-powered companion, navigating life’s experiences alongside you.": "EVA: tu compañera personal con inteligencia artificial, a tu lado en cada experiencia de la vida.",
  "Explore Features": "Explorar características",
  "AI Companion": "Compañera de IA",
  "I have an important appointment this afternoon.": "Tengo una cita importante esta tarde.",
  "I'll remember that. You can continue our conversation later from another device.": "Lo recordaré. Puedes continuar nuestra conversación más tarde desde otro dispositivo.",
  "Product Features": "Características del producto",
  "From a Single Device to a Continuous Companion": "De un solo dispositivo a una compañía continua",
  "Physical Presence": "Presencia física",
  "At home, an embodied companion robot interacts through voice, vision, expressive displays, and physical motion.": "En casa, un robot de compañía interactúa mediante voz, visión, expresiones y movimiento físico.",
  "Shared Intelligence": "Inteligencia compartida",
  "Both embodiments access the same user identity, profile, long-term memory, and cloud AI services.": "Ambas formas comparten la misma identidad, perfil, memoria a largo plazo y servicios de IA en la nube.",
  "Cross-Device Continuity": "Continuidad entre dispositivos",
  "Move between the home robot and the browser-based digital human while preserving persistent personalized context.": "Alterna entre el robot doméstico y el humano digital del navegador sin perder el contexto personalizado.",
  "One Companion Across Daily Life": "Una compañera para cada momento de la vida",
  "At Home — Physical Robot": "En casa — Robot físico",
  "The home robot provides embodied interaction through voice, vision, expression, and motion.": "El robot doméstico ofrece interacción física mediante voz, visión, expresiones y movimiento.",
  "On the Go — Web Digital Human": "Fuera de casa — Humano digital web",
  "Access the same companion from a smartphone or computer browser while away from home.": "Accede a la misma compañera desde el navegador de un teléfono o un ordenador cuando estés fuera de casa.",
  "Across Environments — Shared Context": "Entre entornos — Contexto compartido",
  "The same identity, profile, and long-term memory support personalized interaction across both embodiments.": "La misma identidad, perfil y memoria a largo plazo permiten una interacción personalizada en ambas formas.",
  "Experience OneCompanion": "Conoce OneCompanion",
  "Digital Companion Experience": "Experiencia de compañía digital",
  "The demo supports text, voice, and optional camera input, avatar switching, personalized AI responses, and synchronized digital-human playback.": "La demostración admite texto, voz y cámara opcional, cambio de avatar, respuestas personalizadas de IA y reproducción sincronizada del humano digital.",
  "Launch Demo": "Iniciar demostración",
  "Cross-Device AI Companion": "Compañera de IA multidispositivo",
  "AI Service Status": "Estado del servicio de IA",
  "AI Service Unavailable": "Servicio de IA no disponible",
  "The AI companion service is not connected at the moment. Please try again shortly.": "El servicio de compañía de IA no está conectado en este momento. Inténtalo de nuevo en unos instantes.",
  "Close": "Cerrar",
  "Check Again": "Comprobar de nuevo",

  "AI Companion": "Compañera de IA",
  "Multimodal Interaction": "Interacción multimodal",
  "Digital Human": "Humano digital",
  "Demo Access": "Acceso a la demostración",
  "Enter Access Code": "Introduce el código de acceso",
  "An access code is required to use the current demo service.": "Se necesita un código de acceso para utilizar la demostración.",
  "Access Code": "Código de acceso",
  "Enter access code": "Introduce el código de acceso",
  "Enter Demo": "Entrar en la demostración",
  "Account": "Cuenta",
  "Sign In": "Iniciar sesión",
  "Sign in to keep your persistent user identity across future interactions.": "Inicia sesión para conservar tu identidad de usuario en futuras interacciones.",
  "Username": "Nombre de usuario",
  "Enter username": "Introduce el nombre de usuario",
  "Password": "Contraseña",
  "Enter password": "Introduce la contraseña",
  "Cancel": "Cancelar",
  "Register": "Registrarse",
  "Sign Out": "Cerrar sesión",
  "Create Account": "Crear una cuenta",
  "Register and Sign In": "Registrarse e iniciar sesión",
  "Your current session will be linked to your persistent user identity.": "La sesión actual se vinculará a tu identidad de usuario permanente.",

  "B · Conversation": "B · Conversación",
  "Conversation": "Conversación",
  "Synchronized Avatar Response": "Respuesta sincronizada del avatar",
  "Generating response and avatar...": "Generando la respuesta y el avatar...",
  "C · Camera": "C · Cámara",
  "Camera Preview": "Vista previa de la cámara",
  "Camera Off": "Cámara apagada",
  "Camera On": "Cámara encendida",
  "Camera Preview On": "Vista previa activa",
  "Camera preview is currently off": "La vista previa de la cámara está desactivada",
  "Enable the camera below to use visual emotion recognition. Text and voice conversations remain available while the camera is off.": "Activa la cámara para usar el reconocimiento visual de emociones. El texto y la voz siguen disponibles con la cámara apagada.",
  "Live Preview": "Vista en directo",
  "C · Input": "C · Entrada",
  "Message": "Mensaje",
  "Text / Voice / Video": "Texto / Voz / Vídeo",
  "Type a message or use voice input.": "Escribe un mensaje o usa la entrada de voz.",
  "Recording...": "Grabando...",
  "Send": "Enviar",
  "Sending...": "Enviando...",
  "Start Voice Input": "Iniciar entrada de voz",
  "Stop Recording": "Detener grabación",
  "Processing Voice": "Procesando voz",
  "Use your microphone for a voice interaction. Click again to stop and send.": "Usa el micrófono para hablar. Vuelve a pulsar para detener y enviar.",
  "Recording. Text input is temporarily locked until this voice turn ends.": "Grabando. La entrada de texto está bloqueada hasta que termine este turno de voz.",
  "Stopping the recording and preparing to send.": "Deteniendo la grabación y preparando el envío.",
  "Enable Camera": "Activar cámara",
  "Disable Camera": "Desactivar cámara",
  "Camera Status": "Estado de la cámara",
  "Live preview with recent-frame buffering": "Vista en directo con búfer de fotogramas recientes",
  "No frames attached": "Sin fotogramas adjuntos",
  "Capturing camera frames for this turn.": "Capturando fotogramas de cámara para este turno.",
  "The camera is on, but no video frames were attached to this turn.": "La cámara está activa, pero no se adjuntaron fotogramas a este turno.",

  "Supportive Companion": "Compañera comprensiva",
  "Casual Companion": "Compañera informal",
  "Switch Avatar": "Cambiar avatar",
  "Default Avatar": "Avatar predeterminado",
  "D · Avatar Source": "D · Fuente del avatar",
  "Paste an external avatar page or video URL": "Pega la URL de una página o vídeo de avatar externo",
  "Connect": "Conectar",
  "Disconnect": "Desconectar",
  "The default avatar is active. Connect an external avatar page or video URL here.": "El avatar predeterminado está activo. Puedes conectar aquí una página o vídeo de avatar externo.",
  "The default avatar is active.": "El avatar predeterminado está activo.",
  "External source disconnected. The default avatar is active.": "Fuente externa desconectada. El avatar predeterminado está activo.",
  "External Page": "Página externa",
  "External Video": "Vídeo externo",
  "External Page Error": "Error de página externa",
  "External Video Error": "Error de vídeo externo",
  "Avatar Portrait": "Retrato del avatar",
  "External Avatar": "Avatar externo",

  "Waiting for AI Service": "Esperando al servicio de IA",
  "Multimodal Ready": "Sistema multimodal listo",
  "Details⌄": "Detalles⌄",
  "Hide Details⌃": "Ocultar detalles⌃",
  "A · Status": "A · Estado",
  "Service Status": "Estado del servicio",
  "Secure Connection": "Conexión segura",
  "Status": "Estado",
  "AI Service": "Servicio de IA",
  "Input Mode": "Modo de entrada",
  "Emotion Style": "Estilo emocional",
  "Expression": "Expresión",
  "Motion": "Movimiento",
  "Audio": "Audio",
  "Vision": "Visión",
  "System": "Sistema",
  "You": "Tú",
  "OneCompanion": "OneCompanion",

  "Preparing Service": "Preparando el servicio",
  "Connecting to AI Service": "Conectando con el servicio de IA",
  "Waiting for Voice Input": "Esperando entrada de voz",
  "Waiting for First Interaction": "Esperando la primera interacción",
  "Waiting for Access Code": "Esperando el código de acceso",
  "AI Service Connected": "Servicio de IA conectado",
  "AI Service Error": "Error del servicio de IA",
  "AI Service Processing": "El servicio de IA está procesando",
  "AI Service Ready": "Servicio de IA listo",
  "Sending Request": "Enviando solicitud",
  "Waiting for AI Response": "Esperando la respuesta de la IA",
  "Waiting to Generate": "Esperando para generar",
  "Generating Response": "Generando respuesta",
  "Waiting for Avatar Response": "Esperando la respuesta del avatar",
  "Text and audio are ready. Generating synchronized avatar video.": "El texto y el audio están listos. Generando el vídeo sincronizado del avatar.",
  "Response and avatar are ready": "La respuesta y el avatar están listos",
  "Response complete; avatar video generation failed": "Respuesta completada; falló la generación del vídeo del avatar",
  "Request Failed": "Error en la solicitud",
  "Service Initialization Failed": "Error al iniciar el servicio",
  "Service Connection Error": "Error de conexión con el servicio",
  "Text Input": "Entrada de texto",
  "Voice Input": "Entrada de voz",
  "Text Processed": "Texto procesado",
  "Voice Processed": "Voz procesada",
  "Visual Keyframes Processed": "Fotogramas visuales procesados",
  "Text Send Failed": "Error al enviar el texto",
  "Voice Send Failed": "Error al enviar la voz",
  "Visual Input Send Failed": "Error al enviar la entrada visual",
  "text": "texto",
  "audio": "audio",
  "supportive": "comprensivo",
  "neutral": "neutral",
  "steady": "estable",
  "soft_concern": "preocupación serena",
  "warm_smile": "sonrisa cálida",
  "slow_nod": "asentimiento lento",

  "EVA is ready. Type a message or use voice input to begin.": "EVA está lista. Escribe un mensaje o usa la entrada de voz para comenzar.",
  "The service is preparing. Please try again shortly.": "El servicio se está preparando. Inténtalo de nuevo en unos instantes.",
  "Enter an access code first.": "Introduce primero un código de acceso.",
  "Enter an access code.": "Introduce un código de acceso.",
  "The previous interaction is still processing. Please wait.": "La interacción anterior sigue procesándose. Espera un momento.",
  "Type a message or record a voice message first.": "Escribe un mensaje o graba primero un mensaje de voz.",
  "[Voice Message]": "[Mensaje de voz]",
  "The connection expired. Reconnecting to the service; please resend your last message.": "La conexión ha caducado. Reconectando con el servicio; vuelve a enviar tu último mensaje.",
  "An interaction is already processing. Please wait for it to finish.": "Ya hay una interacción en curso. Espera a que termine.",
  "The demo is busy. Please try again shortly.": "La demostración está ocupada. Inténtalo de nuevo en unos instantes.",
  "Too many attempts. Please try again later.": "Demasiados intentos. Inténtalo de nuevo más tarde.",
  "AI Service temporarily unavailable. Please try again shortly.": "El servicio de IA no está disponible temporalmente. Inténtalo de nuevo en unos instantes.",
  "Service initialization failed. Refresh the page and try again.": "No se pudo iniciar el servicio. Actualiza la página e inténtalo de nuevo.",
  "The access code is invalid or has expired.": "El código de acceso no es válido o ha caducado.",
  "Enter both username and password.": "Introduce el nombre de usuario y la contraseña.",
  "Registration successful. You are now signed in.": "Registro completado. Ya has iniciado sesión.",
  "Signed in successfully.": "Has iniciado sesión correctamente.",
  "This username is already registered.": "Este nombre de usuario ya está registrado.",
  "Account operation failed. Please try again later.": "No se pudo completar la operación de la cuenta. Inténtalo de nuevo más tarde.",
  "Sign out failed. Please try again shortly.": "No se pudo cerrar la sesión. Inténtalo de nuevo en unos instantes.",
  "You have signed out. The current anonymous session can continue.": "Has cerrado la sesión. Puedes continuar con la sesión anónima actual.",
  "No voice content was recorded for this turn.": "No se grabó contenido de voz en este turno.",
  "Voice capture failed.": "Error al capturar la voz.",
  "Voice processing failed.": "Error al procesar la voz.",
  "Camera capture failed.": "Error al capturar la cámara.",
  "Camera preview is not ready yet.": "La vista previa de la cámara aún no está lista.",
  "Capture skipped": "Captura omitida",
  "Input cleared. You can continue the conversation.": "Entrada borrada. Puedes continuar la conversación.",
  "Please provide a non-empty URL before connecting.": "Introduce una URL antes de conectar.",
  "Failed to bind the media URL. Check format and try again.": "No se pudo conectar la URL multimedia. Comprueba el formato e inténtalo de nuevo.",
};

const TEXT_PATTERNS = [
  [/^Turn (\d+) · Text Input$/, "Turno $1 · Entrada de texto"],
  [/^Turn (\d+) · Voice Input$/, "Turno $1 · Entrada de voz"],
  [/^Queued: position (\d+)$/, "En cola: posición $1"],
  [/^Voice attached \((\d+) ms\)$/, "Voz adjunta ($1 ms)"],
  [/^(\d+) video frames attached$/, "$1 fotogramas de vídeo adjuntos"],
  [/^(\d+) camera frames attached$/, "$1 fotogramas de cámara adjuntos"],
  [/^Emotion (.+)$/, "Emoción: $1"],
  [/^Expression (.+)$/, "Expresión: $1"],
  [/^Motion (.+)$/, "Movimiento: $1"],
  [/^Request failed: (.+)$/, "Error en la solicitud: $1"],
  [/^Page (.+) was not found\. You have been returned to the product home page\.$/, "No se encontró la página $1. Te hemos devuelto a la página principal del producto."],
  [/^View Avatar (\d+)$/, "Ver avatar $1"],
];

const textSources = new WeakMap();
const attributeSources = new WeakMap();
let currentLanguage = "en";
let observer = null;
let observedRoot = null;
let toggleButton = null;

function readSavedLanguage() {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return SUPPORTED_LANGUAGES.has(saved) ? saved : "en";
  } catch {
    return "en";
  }
}

function saveLanguage(language) {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Language still works for the current page when storage is unavailable.
  }
}

function translateCore(source) {
  if (currentLanguage !== "es") {
    return source;
  }
  if (Object.prototype.hasOwnProperty.call(ES, source)) {
    return ES[source];
  }
  for (const [pattern, replacement] of TEXT_PATTERNS) {
    if (pattern.test(source)) {
      return source.replace(pattern, replacement);
    }
  }
  return source;
}

function translateValue(source) {
  const match = String(source ?? "").match(/^(\s*)(.*?)(\s*)$/s);
  if (!match) {
    return source;
  }
  return `${match[1]}${translateCore(match[2])}${match[3]}`;
}

function shouldSkipTextNode(node) {
  const parent = node.parentElement;
  return !parent || parent.closest("script, style, [data-i18n-ignore]");
}

function translateTextNode(node, captureSource = false) {
  if (shouldSkipTextNode(node)) {
    return;
  }
  if (captureSource || !textSources.has(node)) {
    textSources.set(node, node.nodeValue || "");
  }
  node.nodeValue = translateValue(textSources.get(node));
}

function translateElementAttributes(element, captureSource = false) {
  if (!(element instanceof Element) || element.closest("[data-i18n-ignore]")) {
    return;
  }
  const names = ["placeholder", "aria-label", "title"];
  let sources = attributeSources.get(element);
  if (!sources) {
    sources = new Map();
    attributeSources.set(element, sources);
  }
  names.forEach((name) => {
    if (!element.hasAttribute(name)) {
      return;
    }
    if (captureSource || !sources.has(name)) {
      sources.set(name, element.getAttribute(name) || "");
    }
    element.setAttribute(name, translateValue(sources.get(name)));
  });
}

function translateTree(root, captureSource = false) {
  if (!root) {
    return;
  }
  if (root.nodeType === Node.TEXT_NODE) {
    translateTextNode(root, captureSource);
    return;
  }
  if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) {
    return;
  }
  if (root.nodeType === Node.ELEMENT_NODE) {
    translateElementAttributes(root, captureSource);
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    if (node.nodeType === Node.TEXT_NODE) {
      translateTextNode(node, captureSource);
    } else {
      translateElementAttributes(node, captureSource);
    }
    node = walker.nextNode();
  }
}

function observe() {
  observer?.observe(observedRoot, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: ["placeholder", "aria-label", "title"],
  });
}

function updateToggle() {
  if (!toggleButton) {
    return;
  }
  const spanishActive = currentLanguage === "es";
  toggleButton.textContent = spanishActive ? "🌐 English" : "🌐 Español";
  toggleButton.setAttribute(
    "aria-label",
    spanishActive ? "Cambiar la interfaz a inglés" : "Switch the interface to Spanish",
  );
  toggleButton.setAttribute("title", spanishActive ? "Cambiar a inglés" : "Switch to Spanish");
}

export function setLanguage(language) {
  currentLanguage = SUPPORTED_LANGUAGES.has(language) ? language : "en";
  saveLanguage(currentLanguage);
  document.documentElement.lang = currentLanguage;
  observer?.disconnect();
  translateTree(observedRoot);
  updateToggle();
  observe();
  window.dispatchEvent(new CustomEvent("onecompanion:languagechange", {
    detail: { language: currentLanguage },
  }));
}

export function initializeI18n({ root = document.body } = {}) {
  observedRoot = root;
  currentLanguage = readSavedLanguage();

  toggleButton = document.createElement("button");
  toggleButton.type = "button";
  toggleButton.className = "language-toggle";
  toggleButton.dataset.i18nIgnore = "true";
  toggleButton.addEventListener("click", () => {
    setLanguage(currentLanguage === "en" ? "es" : "en");
  });
  document.body.appendChild(toggleButton);

  observer = new MutationObserver((mutations) => {
    observer.disconnect();
    mutations.forEach((mutation) => {
      if (mutation.type === "characterData") {
        translateTextNode(mutation.target, true);
        return;
      }
      if (mutation.type === "attributes") {
        translateElementAttributes(mutation.target, true);
        return;
      }
      mutation.addedNodes.forEach((node) => translateTree(node, true));
    });
    observe();
  });

  translateTree(observedRoot, true);
  document.documentElement.lang = currentLanguage;
  updateToggle();
  observe();
}
