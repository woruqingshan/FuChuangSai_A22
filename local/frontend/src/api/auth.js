function resolveApiEndpoint(path) {
  const directApiBase = import.meta.env.VITE_USE_DIRECT_API === "true"
    ? import.meta.env.VITE_API_BASE
    : "";

  if (directApiBase) {
    return `${directApiBase.replace(/\/$/, "")}${path}`;
  }

  return `/api${path}`;
}

export async function fetchAuthMe() {
  return await requestAuth("/auth/me", { method: "GET" });
}

export async function registerAccount({ username, password }) {
  return await requestAuth("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function loginAccount({ username, password }) {
  return await requestAuth("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function logoutAccount() {
  return await requestAuth("/auth/logout", { method: "POST" });
}

async function requestAuth(path, options) {
  const response = await fetch(resolveApiEndpoint(path), {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
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
