const VALUE_LABELS = {
  text: "文字输入",
  audio: "语音输入",
  supportive: "支持鼓励",
  listening: "认真倾听",
  gentle: "温和安抚",
  neutral: "自然",
  neutral_smile: "自然微笑",
  smile: "微笑",
  attentive: "专注",
  steady: "平稳",
  slow_nod: "轻轻点头",
  nod: "点头",
  idle: "空闲",
};

const STATUS_LABELS = {
  "Waiting for first message": "等待首次对话",
  "Remote link pending": "等待连接远端服务",
  "Audio idle": "语音空闲",
  "Camera disabled": "摄像头已关闭",
  "Sending request to local edge-backend": "正在发送到本地服务",
  "Awaiting remote orchestrator response": "等待远端智能服务回复",
  "Text only": "仅文字输入",
  "Request completed": "请求已完成",
  "Remote reply received": "已收到远端回复",
  "Remote orchestrator connected": "远端智能服务已连接",
  "Remote orchestrator error": "远端智能服务异常",
  "Audio processed by edge-backend": "语音已处理",
  "Text turn processed": "文字已处理",
  "Input cleared and ready for the next turn.": "输入已清空，可以继续对话",
  "Request failed": "请求失败",
  "Check edge-backend and remote orchestrator": "请检查本地服务和远端服务",
  "Audio send failed": "语音发送失败",
  "Text send failed": "文字发送失败",
  "Video send failed": "视频发送失败",
  "Video key frames forwarded by edge-backend": "视频关键帧已发送",
  "Camera disabled. Video key frames will not be attached to turns.": "摄像头已关闭，本轮不会附带视频画面",
  "Camera disabled. No key frames will be attached.": "摄像头已关闭，本轮不会附带视频画面",
  "Camera preview and local rolling buffer enabled": "摄像头预览已开启",
  "Capturing buffered camera key frames for this turn.": "正在采集本轮摄像头画面",
  "Camera was enabled, but no video frames were attached.": "摄像头已开启，但本轮未附带视频画面",
  "Recording audio from microphone. Text input is locked for this turn.": "正在录音，本轮暂时不能输入文字",
  "Stopping microphone capture and preparing the voice turn.": "正在停止录音并准备发送",
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
  return `第 ${turnId} 轮 · ${labelValue(inputMode)}`;
}

export function formatAssistantMeta({ emotionStyle, facialExpression, headMotion }) {
  return `${labelValue(emotionStyle)} · ${labelValue(facialExpression)} / ${labelValue(headMotion)}`;
}
