import { labelStatus, labelValue } from "./displayText";

const STATUS_ITEMS = [
  ["sessionId", "Session"],
  ["streamId", "Stream"],
  ["nextTurnId", "Next Turn"],
  ["transport", "Connection"],
  ["remoteStatus", "Remote"],
  ["inputMode", "Input Mode"],
  ["emotionStyle", "Emotion"],
  ["facialExpression", "Expression"],
  ["headMotion", "Motion"],
  ["audioStatus", "Audio"],
  ["videoStatus", "Video"],
];

const STATUS_VALUE_KEYS = new Set([
  "inputMode",
  "emotionStyle",
  "facialExpression",
  "headMotion",
]);

export function createStatusBar() {
  const element = document.createElement("section");
  element.className = "status-panel";
  element.innerHTML = `
    <div class="panel-heading">
      <div>
        <p class="eyebrow">A · System Status</p>
        <h2>Connection Status</h2>
      </div>
      <span class="chip">Session Active</span>
    </div>
    <div class="status-scroll-shell">
      <dl class="status-grid"></dl>
    </div>
  `;

  const grid = element.querySelector(".status-grid");
  const nodes = new Map();

  for (const [key, label] of STATUS_ITEMS) {
    const item = document.createElement("div");
    item.className = "status-item";
    item.innerHTML = `<dt>${label}</dt><dd>-</dd>`;
    grid.appendChild(item);
    nodes.set(key, item.querySelector("dd"));
  }

  function update(nextState) {
    for (const [key] of STATUS_ITEMS) {
      const node = nodes.get(key);
      if (!node) {
        continue;
      }
      const rawValue = nextState[key];
      node.textContent = STATUS_VALUE_KEYS.has(key) ? labelValue(rawValue) : labelStatus(rawValue);
    }
  }

  return { element, update };
}
