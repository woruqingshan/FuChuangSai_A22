function resolveApiEndpoint(path) {
  const directApiBase = import.meta.env.VITE_USE_DIRECT_API === "true"
    ? import.meta.env.VITE_API_BASE
    : "";

  if (directApiBase) {
    return `${directApiBase.replace(/\/$/, "")}${path}`;
  }

  return `/api${path}`;
}

export async function fetchAccessStatus() {
  const response = await fetch(resolveApiEndpoint("/access/status"), {
    method: "GET",
    credentials: "include",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || `The server returned HTTP ${response.status}.`);
    error.status = response.status;
    throw error;
  }
  return data;
}

export async function verifyAccessCode(code) {
  const response = await fetch(resolveApiEndpoint("/access/verify"), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ code }),
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
