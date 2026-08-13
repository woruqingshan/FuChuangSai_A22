import { labelStatus, labelValue } from "./displayText";

const STATUS_ITEMS = [
  ["sessionId", "会话"],
  ["streamId", "通道"],
  ["nextTurnId", "下一轮"],
  ["transport", "传输"],
  ["remoteStatus", "远端"],
  ["inputMode", "输入方式"],
  ["emotionStyle", "情绪风格"],
  ["facialExpression", "表情"],
  ["headMotion", "动作"],
  ["audioStatus", "语音"],
  ["videoStatus", "视频"],
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
        <p class="eyebrow">A · 运行状态</p>
        <h2>系统连接状态</h2>
      </div>
      <span class="chip">会话已保持</span>
    </div>
    <dl class="status-grid"></dl>
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
