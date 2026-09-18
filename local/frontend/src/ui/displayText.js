const VALUE_LABELS = {
  text: "Text Input",
  audio: "Voice Input",
  supportive: "Supportive",
  listening: "Listening",
  gentle: "Gentle",
  neutral: "Neutral",
  neutral_smile: "Natural Smile",
  soft_concern: "Gentle Concern",
  smile: "Smile",
  attentive: "Attentive",
  steady: "Steady",
  slow_nod: "Gentle Nod",
  nod: "Nod",
  idle: "Idle",
};

const STATUS_LABELS = {
  "Waiting for first message": "Waiting for your first message",
  "Remote link pending": "Connecting to the remote service",
  "Audio idle": "Audio ready",
  "Camera disabled": "Camera off",
  "Sending request to local edge-backend": "Sending to the local service",
  "Awaiting remote orchestrator response": "Waiting for the remote service",
  "Text only": "Text only",
  "Request completed": "Request complete",
  "Remote reply received": "Remote reply received",
  "Remote orchestrator connected": "Remote service connected",
  "Remote orchestrator error": "Remote service error",
  "Audio processed by edge-backend": "Audio processed",
  "Text turn processed": "Text processed",
  "Input cleared and ready for the next turn.": "Ready for your next message",
  "Request failed": "Request failed",
  "Check edge-backend and remote orchestrator": "Check the local and remote services",
  "Audio send failed": "Failed to send audio",
  "Text send failed": "Failed to send text",
  "Video send failed": "Failed to send video",
  "Video key frames forwarded by edge-backend": "Video frames sent",
  "Camera disabled. Video key frames will not be attached to turns.": "Camera off; no video frames will be attached",
  "Camera disabled. No key frames will be attached.": "Camera off; no video frames will be attached",
  "Camera preview and local rolling buffer enabled": "Camera preview on",
  "Capturing buffered camera key frames for this turn.": "Capturing camera frames for this message",
  "Camera was enabled, but no video frames were attached.": "Camera on, but no video frames were attached",
  "Recording audio from microphone. Text input is locked for this turn.": "Recording; text input is unavailable until you finish",
  "Stopping microphone capture and preparing the voice turn.": "Stopping the recording and preparing to send",
};

export function labelValue(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return VALUE_LABELS[String(value)] || String(value);
}

export function labelStatus(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const text = String(value);
  return STATUS_LABELS[text] || text;
}

export function formatMessageMeta({ turnId, inputMode }) {
  return `Turn ${turnId} · ${labelValue(inputMode)}`;
}

export function formatAssistantMeta({ emotionStyle, facialExpression, headMotion }) {
  return `${labelValue(emotionStyle)} · ${labelValue(facialExpression)} / ${labelValue(headMotion)}`;
}
