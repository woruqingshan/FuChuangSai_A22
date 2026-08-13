export function createChatPanel() {
  const element = document.createElement("section");
  element.className = "chat-panel";
  element.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">B \u00b7 \u5bf9\u8bdd\u8bb0\u5f55</p>
        <h2>\u804a\u5929\u8bb0\u5f55</h2>
      </div>
      <span class="chip">\u8fdc\u7aef\u667a\u80fd\u56de\u590d</span>
    </div>
    <div class="chat-log" data-role="chat-log"></div>
  `;

  const log = element.querySelector('[data-role="chat-log"]');
  let loadingBubble = null;

  function getRoleLabel(role) {
    if (role === "assistant") {
      return "\u6570\u5b57\u4eba\u52a9\u624b";
    }
    if (role === "user") {
      return "\u6211";
    }
    return "\u7cfb\u7edf\u63d0\u793a";
  }

  function addMessage({ role, text, meta }) {
    const card = document.createElement("article");
    card.className = `message-card ${role}`;

    const roleElement = document.createElement("div");
    roleElement.className = "message-role";
    roleElement.textContent = getRoleLabel(role);

    const textElement = document.createElement("p");
    textElement.className = "message-text";
    textElement.textContent = text ?? "";

    card.append(roleElement, textElement);

    if (meta) {
      const metaElement = document.createElement("div");
      metaElement.className = "message-meta";
      metaElement.textContent = meta;
      card.appendChild(metaElement);
    }

    log.appendChild(card);
    log.scrollTop = log.scrollHeight;
  }

  function addSystemMessage(text) {
    addMessage({ role: "system", text });
  }

  function setLoading(isLoading) {
    if (isLoading && !loadingBubble) {
      loadingBubble = document.createElement("article");
      loadingBubble.className = "message-card system loading-indicator";

      const roleElement = document.createElement("div");
      roleElement.className = "message-role";
      roleElement.textContent = getRoleLabel("system");

      const textElement = document.createElement("p");
      textElement.className = "message-text";
      textElement.textContent = "\u6b63\u5728\u7b49\u5f85\u8fdc\u7aef\u56de\u590d...";

      loadingBubble.append(roleElement, textElement);
      log.appendChild(loadingBubble);
      log.scrollTop = log.scrollHeight;
      return;
    }

    if (!isLoading && loadingBubble) {
      loadingBubble.remove();
      loadingBubble = null;
    }
  }

  return {
    element,
    addMessage,
    addSystemMessage,
    setLoading,
  };
}
