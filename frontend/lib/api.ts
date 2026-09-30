// Central API client for SWASTI Backend (Proxied via Next.js rewrites)
const API_BASE_URL = "/api/v1";

export async function fetchApi<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  // SEC-001: Pure HttpOnly cookie authentication via credentials: "include"
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers,
  });

    if (!response.ok) {
      if (response.status === 401 && typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
      let errorDetail = `API Error: ${response.status} ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // ignore json parse error
      }
      const err = new Error(errorDetail);
      (err as any).status = response.status;
      throw err;
    }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  get: <T = any>(url: string) => fetchApi<T>(url, { method: "GET" }),
  post: <T = any>(url: string, body?: any) => fetchApi<T>(url, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: <T = any>(url: string, body?: any) => fetchApi<T>(url, { method: "PATCH", body: body ? JSON.stringify(body) : undefined }),
  delete: <T = any>(url: string) => fetchApi<T>(url, { method: "DELETE" }),
};
