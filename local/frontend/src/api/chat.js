function resolveChatEndpoint() {
  const directApiBase = import.meta.env.VITE_USE_DIRECT_API === "true"
    ? import.meta.env.VITE_API_BASE
    : "";

  if (directApiBase) {
    return `${directApiBase.replace(/\/$/, "")}/chat`;
  }

  return "/api/chat";
}

function resolveJobEndpoint(jobId) {
  const directApiBase = import.meta.env.VITE_USE_DIRECT_API === "true"
    ? import.meta.env.VITE_API_BASE
    : "";

  if (directApiBase) {
    return `${directApiBase.replace(/\/$/, "")}/jobs/${encodeURIComponent(jobId)}`;
  }

  return `/api/jobs/${encodeURIComponent(jobId)}`;
}

const JOB_POLL_INTERVAL_MS = 1500;
const JOB_CHAT_RESPONSE_TIMEOUT_MS = 35 * 60 * 1000;

export async function sendChatRequest(payload, options = {}) {
  const response = await fetch(resolveChatEndpoint(), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "object"
      ? data.detail.message || data.detail.reason
      : data.detail;
    const error = new Error(detail || `The server returned HTTP ${response.status}.`);
    error.status = response.status;
    error.reason = typeof data.detail === "object" ? data.detail.reason : undefined;
    error.jobId = typeof data.detail === "object" ? data.detail.job_id : undefined;
    throw error;
  }

  if (response.status !== 202 || !data.job_id) {
    return data;
  }

  options.onJobStatus?.(data);
  return await waitForChatResponse(data.job_id, options);
}

async function waitForChatResponse(jobId, options) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < JOB_CHAT_RESPONSE_TIMEOUT_MS) {
    await delay(JOB_POLL_INTERVAL_MS);
    const status = await fetchJobStatus(jobId);
    options.onJobStatus?.(status);
    if (status.chat_response_ready && status.chat_response) {
      return status.chat_response;
    }
    if (["failed", "cancelled"].includes(status.status)) {
      const error = new Error(status.error || "本轮生成失败，请稍后再试。");
      error.status = 502;
      throw error;
    }
  }

  const error = new Error("当前生成等待时间较长，请稍后再试。");
  error.status = 504;
  throw error;
}

async function fetchJobStatus(jobId) {
  const response = await fetch(resolveJobEndpoint(jobId), {
    method: "GET",
    credentials: "include",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "object"
      ? data.detail.message || data.detail.reason
      : data.detail;
    const error = new Error(detail || `The server returned HTTP ${response.status}.`);
    error.status = response.status;
    error.reason = typeof data.detail === "object" ? data.detail.reason : undefined;
    throw error;
  }
  return data;
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
