const INPUT_MODE_LABELS = {
  text: "Text Input",
  audio: "Voice Input",
};

export function formatMessageMeta({ turnId, inputMode }) {
  const modeLabel = INPUT_MODE_LABELS[inputMode] || "Multimodal Input";
  return `Turn ${turnId} · ${modeLabel}`;
}

export function formatAssistantMeta({ emotionStyle, facialExpression, headMotion }) {
  const parts = [
    emotionStyle ? `Emotion ${emotionStyle}` : null,
    facialExpression ? `Expression ${facialExpression}` : null,
    headMotion ? `Motion ${headMotion}` : null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "Synchronized Avatar Response";
}
