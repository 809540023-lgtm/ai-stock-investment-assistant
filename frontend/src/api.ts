const TOKEN_KEY = "ai_invest_token";

// 正式環境用 VITE_API_BASE 指向後端網域；開發時留空，走 Vite proxy 的相對路徑 /api
// Render 的 fromService 只給主機名（無 scheme），這裡自動補上 https://
function resolveApiBase(): string {
  let base = (import.meta.env.VITE_API_BASE ?? "").trim().replace(/\/$/, "");
  if (base && !/^https?:\/\//.test(base)) base = "https://" + base;
  return base;
}
const API_BASE = resolveApiBase();
function url(path: string): string {
  return API_BASE + path;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url(path), { ...options, headers });
  if (!res.ok) {
    let detail = `請求失敗 (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type User = { id: number; email: string; name: string };

export type Plan = {
  id: number;
  user_id: number;
  plan_type: "full_analysis" | "recurring_investment";
  stock_symbol: string;
  stock_name: string;
  monthly_amount: number | null;
  initial_amount: number | null;
  investment_years: number | null;
  risk_profile: string | null;
  max_loss_percent: number | null;
  target_return_percent: number | null;
  current_price: number | null;
  average_cost: number | null;
  shares_owned: number | null;
  cash_reserve_ratio: number | null;
  fixed_buy_ratio: number | null;
  ai_summary: string | null;
  fundamental_analysis: string | null;
  valuation_analysis: string | null;
  buy_strategy: string | null;
  add_position_strategy: string | null;
  pause_strategy: string | null;
  sell_strategy: string | null;
  risk_notes: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type UpdateLog = {
  id: number;
  plan_id: number;
  trigger: string;
  price_at_update: number | null;
  ai_summary: string | null;
  action: string | null;
  detail: string | null;
  created_at: string;
};

export type Reminder = {
  id: number;
  plan_id: number;
  kind: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
};

export type Trade = {
  id: number;
  plan_id: number;
  action: "buy" | "sell";
  shares: number;
  price: number;
  note: string | null;
  traded_at: string;
  created_at: string;
};

export type DashboardPlan = {
  id: number;
  stock_symbol: string;
  stock_name: string;
  plan_type: string;
  status: string;
  shares_owned: number;
  average_cost: number | null;
  current_price: number | null;
  invested: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number | null;
};

export type Dashboard = {
  plan_count: number;
  total_invested: number;
  total_market_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_percent: number | null;
  unread_reminders: number;
  plans: DashboardPlan[];
};

export const api = {
  register: (email: string, password: string, name: string) =>
    request<{ access_token: string; user: User }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),

  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(url("/api/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) {
      const b = await res.json().catch(() => ({}));
      throw new Error(b.detail || "登入失敗");
    }
    return res.json() as Promise<{ access_token: string; user: User }>;
  },

  me: () => request<User>("/api/auth/me"),

  createPlan: (payload: Record<string, unknown>) =>
    request<Plan>("/api/plans", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listPlans: () => request<Plan[]>("/api/plans"),
  getPlan: (id: number) => request<Plan>(`/api/plans/${id}`),
  deletePlan: (id: number) =>
    request<{ ok: boolean }>(`/api/plans/${id}`, { method: "DELETE" }),
  analyzePlan: (id: number) =>
    request<Plan>(`/api/plans/${id}/analyze`, { method: "POST" }),
  planUpdates: (id: number) => request<UpdateLog[]>(`/api/plans/${id}/updates`),

  reminders: (unreadOnly = false) =>
    request<Reminder[]>(`/api/reminders${unreadOnly ? "?unread_only=true" : ""}`),
  markReminderRead: (id: number) =>
    request<Reminder>(`/api/reminders/${id}/read`, { method: "POST" }),

  trades: (planId: number) => request<Trade[]>(`/api/plans/${planId}/trades`),
  addTrade: (planId: number, payload: Record<string, unknown>) =>
    request<Plan>(`/api/plans/${planId}/trades`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteTrade: (planId: number, tradeId: number) =>
    request<Plan>(`/api/plans/${planId}/trades/${tradeId}`, { method: "DELETE" }),

  dashboard: () => request<Dashboard>("/api/dashboard"),
};
