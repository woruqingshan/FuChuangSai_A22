function resolveSessionEndpoint() {
  const directApiBase = import.meta.env.VITE_USE_DIRECT_API === "true"
    ? import.meta.env.VITE_API_BASE
    : "";

  if (directApiBase) {
    return `${directApiBase.replace(/\/$/, "")}/session`;
  }

  return "/api/session";
}

export async function bootstrapServerSession() {
  const response = await fetch(resolveSessionEndpoint(), {
    method: "POST",
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
