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
  import_jobs_today?: number;
  contacts_imported_today?: number;
  messages_imported_today?: number;
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
  industry?: string;
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

export async function getLeadsPipeline() {
  return api('/api/dashboard/leads/pipeline');
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

export async function getCampaigns() {
  return api('/api/campaigns');
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

export async function getAIStats() {
  return api('/api/ai/stats');
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

// ─── Import ─────────────────────────────────────────────────────────────────────

export type ImportSource = {
  id: string;
  name: string;
  source_type: string;
  provider: string;
  is_active: boolean;
  last_import_at?: string | null;
  total_contacts_imported: number;
  total_messages_imported: number;
  created_at: string;
};

export type ImportJob = {
  id: string;
  job_type: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  contacts_found: number;
  contacts_created: number;
  contacts_updated: number;
  messages_imported: number;
  conversations_created: number;
  skipped_duplicates: number;
  errors: unknown[];
  warnings: unknown[];
  summary?: string | null;
  created_at: string;
};

export async function getImportSources(): Promise<{ data: ImportSource[] }> {
  return api<{ data: ImportSource[] }>('/api/import/sources');
}

export async function createImportSource(data: Partial<ImportSource>) {
  return api('/api/import/sources', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getImportJobs(
  status?: string,
  page = 1,
  limit = 20,
): Promise<{ data: ImportJob[]; pagination: Record<string, unknown> }> {
  const qs = new URLSearchParams();
  if (status) qs.set('status', status);
  qs.set('page', String(page));
  qs.set('limit', String(limit));
  return api(`/api/import/jobs?${qs}`);
}

export async function runChatImport(data: Record<string, unknown>) {
  return api('/api/import/chats/run', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function startImportJob(jobId: string) {
  return api(`/api/import/chats/${jobId}/start`, { method: 'POST' });
}

export async function triggerContactImport(body: { business_id?: string; dry_run?: boolean }) {
  return api('/api/import/contacts/import', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function getImportHistory(
  business_id?: string,
  page = 1,
  limit = 20,
): Promise<{ data: ImportedChat[]; pagination: Record<string, unknown> }> {
  const qs = new URLSearchParams();
  if (business_id) qs.set('business_id', business_id);
  qs.set('page', String(page));
  qs.set('limit', String(limit));
  return api(`/api/import/history?${qs}`);
}

// ─── Business (Theo Brand / Unit / Location) ──────────────────────────────────

export type BusinessBrand = {
  id: string;
  name: string;
  legal_name?: string;
  tagline?: string;
  industry?: string;
  province?: string;
  city?: string;
  phone?: string;
  email?: string;
  website?: string;
  primary_color?: string;
  currency?: string;
  timezone?: string;
  is_active: boolean;
  units?: unknown[];
  locations?: unknown[];
};

export type BusinessUnit = {
  id: string;
  brand_id: string;
  name: string;
  unit_type?: string;
  manager_name?: string;
  manager_email?: string;
  is_active: boolean;
};

export type BusinessLocation = {
  id: string;
  brand_id: string;
  unit_id?: string;
  name: string;
  location_type?: string;
  address?: string;
  city?: string;
  province?: string;
  phone?: string;
  email?: string;
  whatsapp_number?: string;
  whatsapp_connected: boolean;
  is_active: boolean;
};

export async function getBrands(activeOnly = true): Promise<{ data: BusinessBrand[] }> {
  const qs = new URLSearchParams();
  qs.set('active_only', String(activeOnly));
  return api<{ data: BusinessBrand[] }>(`/api/business/brands?${qs}`);
}

export async function getBrand(id: string): Promise<BusinessBrand> {
  return api<BusinessBrand>(`/api/business/brands/${id}`);
}

export async function createBrand(data: Partial<BusinessBrand>) {
  return api('/api/business/brands', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateBrand(id: string, updates: Partial<BusinessBrand>) {
  return api(`/api/business/brands/${id}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function getUnits(brandId: string): Promise<{ data: BusinessUnit[] }> {
  return api<{ data: BusinessUnit[] }>(`/api/business/brands/${brandId}/units`);
}

export async function createUnit(brandId: string, data: Partial<BusinessUnit>) {
  return api(`/api/business/brands/${brandId}/units`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getLocations(
  brandId: string,
  unitId?: string,
): Promise<{ data: BusinessLocation[] }> {
  const qs = new URLSearchParams();
  if (unitId) qs.set('unit_id', unitId);
  const suffix = qs.toString() ? `?${qs}` : '';
  return api<{ data: BusinessLocation[] }>(`/api/business/brands/${brandId}/locations${suffix}`);
}

export async function createLocation(brandId: string, data: Partial<BusinessLocation>) {
  return api(`/api/business/brands/${brandId}/locations`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function connectLocationWhatsapp(locationId: string, body: {
  session_id: string;
  phone_number: string;
}) {
  return api(`/api/business/locations/${locationId}/connect-whatsapp`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function getPlatformSummary(): Promise<unknown> {
  return api('/api/business/platform/summary');
}


// ─── Util ──────────────────────────────────────────────────────────────────────

export function getAPIBASE(): string {
  return API_BASE;
}

export function isLoggedIn(): boolean {
  return typeof window !== 'undefined' && !!localStorage.getItem('wacrm_token');
}

export function logout() {
  localStorage.removeItem('wacrm_token');
}
