const RAW_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const API_BASE_URL = RAW_URL.replace(/\/api\/v1\/?$/, "");
let csrfToken: string | null = null;

export type AppRole = "PERSONNEL" | "COMMANDER" | "WELFARE_OFFICER" | "ADMIN";

export interface AuthUser {
  id: string;
  username: string;
  role: AppRole;
  unit_id: string | null;
  personnel_id: string | null;
}

export interface OperationalDriver {
  code: string;
  name: string;
  value: number | null;
  weight: number;
}

export interface CommanderOverview {
  unit: { id: string; unit_code: string; unit_name: string; unit_type: string; location_label: string | null; sanctioned_strength: number };
  kpis: { total_personnel: number; available_strength: number | null; required_strength: number | null; coverage_percent: number | null; avg_wsi: number | null; low_risk_count: number; medium_risk_count: number; high_risk_count: number; alert_count: number };
  distribution: { label: string; count: number; color: string; band: string }[];
  drivers: OperationalDriver[];
}

export function getStoredRole(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("prahari_role");
}

export function getStoredUser(): any | null {
  if (typeof window === "undefined") return null;
  const userStr = localStorage.getItem("prahari_user");
  return userStr ? JSON.parse(userStr) : null;
}

export function setStoredSession(role: string, user: any, token?: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("prahari_role", role);
    localStorage.setItem("prahari_user", JSON.stringify(user));
    if (token) localStorage.setItem("prahari_token", token);
  }
}

export function clearStoredSession() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("prahari_token");
    localStorage.removeItem("prahari_role");
    localStorage.removeItem("prahari_user");
  }
}

export const DEMO_CREDENTIALS: Record<string, { u: string; p: string; label: string }> = {
  COMMANDER: { u: "demo_commander", p: "prahari123", label: "Commander (1-BN)" },
  WELFARE_OFFICER: { u: "demo_welfare_officer", p: "prahari123", label: "Welfare Officer" },
  PERSONNEL: { u: "demo_personnel", p: "prahari123", label: "Personnel (Service Member)" },
  ADMIN: { u: "demo_admin", p: "prahari123", label: "System Administrator" },
};

export function generateIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "idem-" + Date.now() + "-" + Math.random().toString(36).substring(2, 10);
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Inject Bearer token if stored in session
  if (!headers.has("Authorization") && typeof window !== "undefined") {
    const token = localStorage.getItem("prahari_token");
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const bearer = /^Bearer\s+\S+/i.test(headers.get("Authorization") || "");
  if (!bearer && options.method && !["GET", "HEAD", "OPTIONS"].includes(options.method.toUpperCase()) && typeof document !== "undefined") {
    if (!headers.has("X-CSRF-Token")) {
      if (!csrfToken) {
        const csrfRes = await request<{ csrf_token: string }>("/api/v1/auth/csrf");
        csrfToken = csrfRes.csrf_token;
      }
      headers.set("X-CSRF-Token", csrfToken);
    }
  }

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: "include", // Ensures HttpOnly cookie prahari_session is sent
  });

  if (!res.ok) {
    let errorMsg = `API Error ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      errorMsg = errJson.error?.message || errJson.detail || errorMsg;
    } catch {
      // fallback text
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

// Authentication
export const authApi = {
  login: async (username: string, password: string) => {
    const bootstrap = await request<{ csrf_token: string }>("/api/v1/auth/csrf?for_login=true");
    const data = await request<{ access_token: string; user: AuthUser; csrf_token: string }>("/api/v1/auth/login", {
      method: "POST",
      headers: { "X-CSRF-Token": bootstrap.csrf_token },
      body: JSON.stringify({ username, password }),
    });
    csrfToken = data.csrf_token;
    setStoredSession(data.user.role, data.user, data.access_token);
    return data;
  },
  me: () => request<AuthUser>("/api/v1/auth/me"),
  refresh: () => request<{ access_token: string }>("/api/v1/auth/refresh", { method: "POST" }),
  logout: async () => {
    try {
      await request<{ message: string }>("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // ignore logout network errors
    } finally {
      clearStoredSession();
      csrfToken = null;
    }
  },
};

// Commander (Unit Aggregates only - Strictly no raw wellbeing answers)
export const commanderApi = {
  getOverview: (unitId?: string) =>
    request<CommanderOverview>(unitId ? `/api/v1/commander/overview?unit_id=${unitId}` : "/api/v1/commander/overview"),
  getPriorityList: (limit = 50, offset = 0) =>
    request<any[]>(`/api/v1/commander/priority-list?limit=${limit}&offset=${offset}`),
  getOperationalAttention: (cursor?: string, limit = 50) =>
    request<{ items: any[]; next_cursor: string | null }>(
      cursor ? `/api/v1/operational/attention?cursor=${encodeURIComponent(cursor)}&limit=${limit}` : `/api/v1/operational/attention?limit=${limit}`
    ),
  getStrainCard: (personnelId: string) =>
    request<any>(`/api/v1/commander/strain-card/${personnelId}`),
  getAlerts: (status?: "OPEN" | "ACKNOWLEDGED" | "RESOLVED", cursor?: string, limit = 50) => {
    const params = new URLSearchParams();
    if (status) params.append("status", status);
    if (cursor) params.append("cursor", cursor);
    params.append("limit", limit.toString());
    return request<{ items: any[]; next_cursor: string | null }>(`/api/v1/alerts?${params.toString()}`);
  },
  acknowledgeAlert: (alertId: string, notes?: string, idempotencyKey?: string) =>
    request<any>(`/api/v1/alerts/${alertId}/acknowledge`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify({ notes: notes || "Acknowledged by commander in operational review" }),
    }),
  resolveAlert: (alertId: string, notes?: string, idempotencyKey?: string) =>
    request<any>(`/api/v1/alerts/${alertId}/resolve`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify({ notes: notes || "Resolved by commander in operational review" }),
    }),
  getScenarios: () => request<any[]>("/api/v1/commander/scenarios"),
  getScenario: (scenarioId: string) => request<any>(`/api/v1/commander/scenarios/${scenarioId}`),
  getScenarioComparison: (scenarioId: string) => request<any>(`/api/v1/commander/scenarios/${scenarioId}/comparison`),
  decideScenario: (scenarioId: string, payload: {
    decision: "ACCEPT" | "MODIFY" | "REJECT";
    expected_revision: string;
    rationale: string;
    modified_changes?: any[];
  }, idempotencyKey?: string) =>
    request<any>(`/api/v1/commander/scenarios/${scenarioId}/decide`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify(payload),
    }),
  getUnit: (unitId?: string) =>
    request<any>(unitId ? `/api/v1/commander/unit?unit_id=${unitId}` : "/api/v1/commander/unit"),
  getUnitStats: (unitId?: string) =>
    request<any>(unitId ? `/api/v1/commander/unit/stats?unit_id=${unitId}` : "/api/v1/commander/unit/stats"),
  getDeployments: (unitId?: string) =>
    request<any>(unitId ? `/api/v1/commander/unit/deployments?unit_id=${unitId}` : "/api/v1/commander/unit/deployments"),
  getLeave: (unitId?: string) =>
    request<any>(unitId ? `/api/v1/commander/unit/leave?unit_id=${unitId}` : "/api/v1/commander/unit/leave"),
  getWorkload: (unitId?: string) =>
    request<any>(unitId ? `/api/v1/commander/unit/workload?unit_id=${unitId}` : "/api/v1/commander/unit/workload"),
  getRiskTrends: (unitId?: string) =>
    request<any[]>(unitId ? `/api/v1/commander/unit/risk-trends?unit_id=${unitId}` : "/api/v1/commander/unit/risk-trends"),
};

// Welfare Officer (Authorized individual search, 7-tab profile, and 4 welfare actions)
export const welfareApi = {
  namedSearch: (payload: { field: "name" | "service_code" | "pseudo_id"; query: string; purpose_reason: string; limit?: number }) =>
    request<{ items: any[]; next_cursor: string | null }>("/api/v1/welfare/personnel/search", {
      method: "POST",
      body: JSON.stringify({
        field: payload.field,
        query: payload.query,
        purpose_reason: payload.purpose_reason || "Authorized welfare case review and personnel support assessment",
        limit: payload.limit || 20,
      }),
    }),
  searchPersonnel: (query?: string, riskFilter?: string, unitId?: string) => {
    const params = new URLSearchParams();
    if (query) params.append("query", query);
    if (riskFilter && riskFilter !== "ALL") params.append("risk_filter", riskFilter);
    if (unitId) params.append("unit_id", unitId);
    return request<any[]>(`/api/v1/welfare/personnel/search?${params.toString()}`);
  },
  openCase: (payload: { personnel_id: string; request_type: "LEAVE_ASSISTANCE" | "STRESS_FATIGUE" | "MEDICAL_HEALTH" | "FAMILY_PERSONAL"; priority?: "NORMAL" | "URGENT"; personnel_visible_reason: string }, idempotencyKey?: string) =>
    request<{ id: string; status: string; assigned_to_me: boolean; created_at: string }>("/api/v1/welfare/cases", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify({
        personnel_id: payload.personnel_id,
        request_type: payload.request_type,
        priority: payload.priority || "NORMAL",
        personnel_visible_reason: payload.personnel_visible_reason,
      }),
    }),
  listCases: (status?: string) =>
    request<any[]>(status ? `/api/v1/welfare/cases?status=${status}` : "/api/v1/welfare/cases"),
  getCaseDetail: (requestId: string) =>
    request<any>(`/api/v1/welfare/cases/${requestId}`),
  updateCase: (requestId: string, payload: { status: string; follow_up_date?: string; notes?: string }) =>
    request<any>(`/api/v1/welfare/cases/${requestId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  assignCase: (requestId: string, reason: string) =>
    request<any>(`/api/v1/welfare/cases/${requestId}/assign`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  reassignCase: (requestId: string, targetOfficerUserId: string, reason: string) =>
    request<any>(`/api/v1/welfare/cases/${requestId}/reassign`, {
      method: "POST",
      body: JSON.stringify({ target_officer_user_id: targetOfficerUserId, reason }),
    }),
  updatePriority: (requestId: string, priority: "NORMAL" | "URGENT", reason: string) =>
    request<any>(`/api/v1/welfare/cases/${requestId}/priority`, {
      method: "POST",
      body: JSON.stringify({ priority, reason }),
    }),
  recordCaseAction: (requestId: string, payload: {
    action_type: string;
    note?: string;
    visibility?: string;
    follow_up_date?: string;
    case_status?: string;
  }) =>
    request<any>(`/api/v1/welfare/cases/${requestId}/actions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPersonnelProfile: (personnelId: string) =>
    request<any>(`/api/v1/welfare/personnel/${personnelId}`),
  getPersonnelHistory: (personnelId: string) =>
    request<any>(`/api/v1/welfare/personnel/${personnelId}/history`),
  getPersonnelRisk: (personnelId: string) =>
    request<any>(`/api/v1/welfare/personnel/${personnelId}/risk`),
  getPersonnelWellbeing: (personnelId: string) =>
    request<any>(`/api/v1/welfare/personnel/${personnelId}/wellbeing`),
  getPersonnelFactors: (personnelId: string) =>
    request<any[]>(`/api/v1/welfare/personnel/${personnelId}/factors`),
  recordWelfareAction: (personnelId: string, payload: {
    action_type: "MONITOR" | "CONTACT_PERSONNEL" | "WELFARE_FOLLOWUP" | "RECORD_OUTCOME";
    details: string;
    notes?: string;
    follow_up_date?: string;
    outcome?: string;
  }) =>
    request<any>(`/api/v1/welfare/personnel/${personnelId}/actions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAlerts: (status?: "OPEN" | "ACKNOWLEDGED" | "RESOLVED", cursor?: string, limit = 50) => {
    const params = new URLSearchParams();
    if (status) params.append("status", status);
    if (cursor) params.append("cursor", cursor);
    params.append("limit", limit.toString());
    return request<{ items: any[]; next_cursor: string | null }>(`/api/v1/alerts?${params.toString()}`);
  },
};

// Personnel (Own profile, deployments, duties, rest, leave, voluntary self-check, risk, support requests)
export const personnelApi = {
  getProfile: () => request<any>("/api/v1/personnel/me"),
  getMyDeployments: () => request<any[]>("/api/v1/personnel/me/deployments"),
  getMyDuties: () => request<any[]>("/api/v1/personnel/me/duties"),
  getMyRest: () => request<any[]>("/api/v1/personnel/me/rest"),
  getMyLeave: () => request<any[]>("/api/v1/personnel/me/leave"),
  getMyRisk: () => request<any>("/api/v1/personnel/me/risk"),
  getMyWellbeing: () => request<any>("/api/v1/personnel/me/wellbeing"),
  getConsent: () => request<any>("/api/v1/personnel/consent"),
  updateConsent: (action: "CONSENT" | "WITHDRAW") =>
    request<any>("/api/v1/personnel/consent", {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  submitSelfCheck: (answers: Record<string, any>) =>
    request<any>("/api/v1/personnel/me/wellbeing", {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
  listSelfChecks: () => request<any[]>("/api/v1/personnel/self-checks"),
  createSupportRequest: (payload: { request_type: string; priority: string; details: string }) =>
    request<any>("/api/v1/personnel/support-request", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listSupportRequests: () => request<any[]>("/api/v1/personnel/support-requests"),
  getPrivacyHistory: () => request<any[]>("/api/v1/personnel/privacy-history"),
  getNotifications: () => request<any[]>("/api/v1/notifications"),
  markNotificationRead: (notificationId: string) =>
    request<any>(`/api/v1/notifications/${notificationId}/read`, { method: "POST" }),
};

// Admin (Users, Personnel, Units, System Health, Policies, CSV Ingestion, Master Writes)
export const adminApi = {
  getHealth: () => request<any>("/api/v1/admin/health"),
  listUsers: (limit = 100, offset = 0) =>
    request<any[]>(`/api/v1/admin/users?limit=${limit}&offset=${offset}`),
  createUser: (payload: { username: string; password: string; role: string; unit_id?: string; personnel_id?: string }) =>
    request<any>("/api/v1/admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateUser: (userId: string, payload: { is_active?: boolean; role?: string }) =>
    request<any>(`/api/v1/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  listPersonnel: (limit = 100, offset = 0) =>
    request<any[]>(`/api/v1/admin/personnel?limit=${limit}&offset=${offset}`),
  createPersonnel: (payload: {
    unit_id: string;
    personnel_code: string;
    full_name: string;
    pseudo_id?: string;
    rank_or_grade: string;
    role_title: string;
    service_years: number;
    status?: string;
    joining_date?: string;
  }, idempotencyKey?: string) =>
    request<any>("/api/v1/admin/personnel", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify(payload),
    }),
  transferPersonnel: (personnelId: string, payload: { target_unit_id: string; reason_code?: string; reason?: string }, idempotencyKey?: string) =>
    request<any>(`/api/v1/admin/personnel/${personnelId}/transfer`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify({
        target_unit_id: payload.target_unit_id,
        reason_code: payload.reason_code || payload.reason || "OPERATIONAL_NEED",
      }),
    }),
  listUnits: () => request<any[]>("/api/v1/admin/units"),
  createUnit: (payload: {
    unit_code: string;
    unit_name: string;
    unit_type: string;
    location_label?: string;
    sanctioned_strength: number;
  }, idempotencyKey?: string) =>
    request<any>("/api/v1/admin/units", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify(payload),
    }),
  listSkills: (limit = 100, offset = 0) =>
    request<{ items: any[]; next_offset: number | null }>(`/api/v1/admin/skills?limit=${limit}&offset=${offset}`),
  createSkill: (payload: { skill_code: string; skill_name: string; category: string }, idempotencyKey?: string) =>
    request<any>("/api/v1/admin/skills", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify(payload),
    }),
  listPolicies: () => request<any[]>("/api/v1/admin/policies"),
  getModels: () => request<any>("/api/v1/admin/models"),
  getJobs: (limit = 50, offset = 0) =>
    request<{ items: any[]; next_offset: number | null; scheduler_cadence: string; status: string; scheduler_status: string }>(
      `/api/v1/admin/jobs?limit=${limit}&offset=${offset}`
    ),
  getAudit: (limit = 100, offset = 0) =>
    request<any[]>(`/api/v1/admin/audit?limit=${limit}&offset=${offset}`),
  getImportTemplates: () =>
    request<{ max_rows: number; max_bytes: number; datasets: { dataset_type: string; fields: any[] }[] }>(
      "/api/v1/admin/imports/templates"
    ),
  validateImport: (payload: {
    dataset_type: "duties" | "rest_records" | "leave_records" | "deployments" | "training" | "staffing";
    csv_data: string;
    source_timestamp: string;
  }) =>
    request<{
      id: string;
      status: "VALIDATED" | "REJECTED";
      dataset_type: string;
      checksum: string;
      revision: string;
      row_count: number;
      errors: { row: number; field: string; error: string; raw_value: string }[];
    }>("/api/v1/admin/imports/validate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  commitImport: (
    importId: string,
    payload: {
      dataset_type: "duties" | "rest_records" | "leave_records" | "deployments" | "training" | "staffing";
      csv_data: string;
      source_timestamp: string;
      checksum: string;
      expected_revision: string;
    },
    idempotencyKey?: string
  ) =>
    request<{
      id: string;
      status: string;
      dataset_type: string;
      row_count: number;
      source_hash: string;
      revision: string;
      committed_at: string;
    }>(`/api/v1/admin/imports/${importId}/commit`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify(payload),
    }),
  getImportHistory: (limit = 50, offset = 0, datasetType?: string, status?: string) => {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());
    params.append("offset", offset.toString());
    if (datasetType) params.append("dataset_type", datasetType);
    if (status) params.append("status", status);
    return request<{ items: any[]; next_offset: number | null }>(`/api/v1/admin/imports?${params.toString()}`);
  },
  triggerOperationalRun: (payload: { cutoff: string; unit_id?: string }, idempotencyKey?: string) =>
    request<any>("/api/v1/admin/operational-runs", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey || generateIdempotencyKey() },
      body: JSON.stringify({
        cutoff: payload.cutoff,
        ...(payload.unit_id ? { unit_id: payload.unit_id } : {}),
      }),
    }),
};

