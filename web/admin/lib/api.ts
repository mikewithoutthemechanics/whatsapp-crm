const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

// ─── Types ───────────────────────────────────────────────────────────────────

export type LoginInput = { email: string; password: string };
export type LoginResponse = { token: string; expires_in: number };
export type DashboardSummary = {
  total_conversations: number;
  active_conversations: number;
  ai_handled: number;
  messages_today: number;
  new_leads_today: number;
  converted_leads: number;
  ai_requests_today: { groq: number; openrouter: number };
  campaigns_active: number;
  campaign_subscribers: number;
};
export type Conversation = {
  id: string;
  status: string;
  contact: { name: string; phone: string };
  last_message?: { text: string; at: string };
};
export type Contact = {
  id: string;
  first_name: string;
  last_name: string;
  whatsapp_number: string;
  display_name: string;
  lead_status: string;
  lead_score: number;
  tags: string[];
  province: string;
  city: string;
  lead_source: string;
  created_at: string;
};
export type Campaign = {
  id: string;
  name: string;
  campaign_type: string;
  trigger_event: string;
  status: string;
  sent_count: number;
  delivered_count: number;
  replied_count: number;
  active_subscribers: number;
};
export type LeadsPipeline = {
  pipeline: {
    new: { count: number; contacts: unknown[] };
    contacted: { count: number; contacts: unknown[] };
    qualified: { count: number; contacts: unknown[] };
    converted: { count: number; contacts: unknown[] };
    inactive: { count: number; contacts: unknown[] };
  };
};
export type AIStats = {
  provider?: string;
  current_provider?: string;
  groq_requests?: number;
  openrouter_requests?: number;
  after_hours?: boolean;
  groq_free_tier_remaining?: number;
  groq_free_tier_daily?: number;
  top_intents?: { intent: string; count: number }[];
};

// ─── Auth helper ─────────────────────────────────────────────────────────────

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('wacrm_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Core fetch wrapper ──────────────────────────────────────────────────────

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok && res.status !== 204) {
    const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail?: string;
    };
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function login(data: LoginInput): Promise<LoginResponse> {
  return api<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return api<DashboardSummary>('/api/dashboard/summary');
}

export async function getActiveConversations(
  limit = 25,
): Promise<{ data: Conversation[] }> {
  return api<{ data: Conversation[] }>(
    `/api/dashboard/conversations/active?limit=${limit}`,
  );
}

export async function getLeadsPipeline(): Promise<LeadsPipeline> {
  return api<LeadsPipeline>('/api/dashboard/leads/pipeline');
}

// ─── Contacts ────────────────────────────────────────────────────────────────

export async function getContacts(params: {
  page?: number;
  limit?: number;
  search?: string;
  lead_status?: string;
  tag?: string;
  tag_ids?: string;
}): Promise<{ data: Contact[]; pagination: Record<string, unknown> }> {
  const qs = new URLSearchParams();
  if (params.page) qs.set('page', String(params.page));
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.search) qs.set('search', params.search);
  if (params.lead_status) qs.set('lead_status', params.lead_status);
  if (params.tag) qs.set('tag', params.tag);
  if (params.tag_ids) qs.set('tag_ids', params.tag_ids);
  return api(`/api/contacts?${qs}`);
}

export async function getContact(id: string): Promise<Contact> {
  return api<Contact>(`/api/contacts/${id}`);
}

// ─── Messages ────────────────────────────────────────────────────────────────

export async function sendMessage(data: { to: string; content: string; type?: string }) {
  return api('/api/messages/send', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function quickReply(data: { reply_key: string; to: string }) {
  return api('/api/messages/quick-reply', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ─── Campaigns ───────────────────────────────────────────────────────────────

export async function getCampaigns(): Promise<Campaign[]> {
  return api<Campaign[]>('/api/campaigns');
}

export async function createCampaign(data: Record<string, unknown>) {
  return api('/api/campaigns', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function activateCampaign(id: string) {
  return api(`/api/campaigns/${id}/activate`, { method: 'POST' });
}

export async function pauseCampaign(id: string) {
  return api(`/api/campaigns/${id}/pause`, { method: 'POST' });
}

export async function broadcastCampaign(
  id: string,
  data: Record<string, unknown>,
) {
  return api(`/api/campaigns/${id}/broadcast`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ─── AI ──────────────────────────────────────────────────────────────────────

export async function getAIStats(): Promise<AIStats> {
  return api<AIStats>('/api/ai/stats');
}

// ─── Admin ───────────────────────────────────────────────────────────────────

export async function getHealthDetailed() {
  return api('/api/admin/health/detailed');
}

export async function getOpenWAHealth() {
  return api('/api/admin/webhooks/openwa/health');
}

export async function getSessions() {
  return api('/api/admin/sessions');
}

// ─── Util ────────────────────────────────────────────────────────────────────

export function getAPIBASE(): string {
  return API_BASE;
}

export function isLoggedIn(): boolean {
  return typeof window !== 'undefined' && !!localStorage.getItem('wacrm_token');
}

export function logout() {
  localStorage.removeItem('wacrm_token');
}
