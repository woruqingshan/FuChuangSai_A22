export function createChatPanel() {
  const element = document.createElement("section");
  element.className = "chat-panel";
  element.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">B · Conversation</p>
        <h2>Chat History</h2>
      </div>
      <span class="chip">AI Replies</span>
    </div>
    <div class="chat-log" data-role="chat-log"></div>
  `;

  const log = element.querySelector('[data-role="chat-log"]');
  let loadingBubble = null;

  function getRoleLabel(role) {
    if (role === "assistant") {
      return "Digital Human";
    }
    if (role === "user") {
      return "You";
    }
    return "System";
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
      textElement.textContent = "Waiting for the remote reply...";

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
