const INPUT_MODE_LABELS = {
  text: "文字输入",
  audio: "语音输入",
};

export function formatMessageMeta({ turnId, inputMode }) {
  const modeLabel = INPUT_MODE_LABELS[inputMode] || "多模态输入";
  return `第 ${turnId} 轮 · ${modeLabel}`;
}

export function formatAssistantMeta({ emotionStyle, facialExpression, headMotion }) {
  const parts = [
    emotionStyle ? `情绪 ${emotionStyle}` : null,
    facialExpression ? `表情 ${facialExpression}` : null,
    headMotion ? `动作 ${headMotion}` : null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "同步数字人回复";
}
