import axios from 'axios';

// Empty baseURL → all '/api/*' calls route through the Next.js proxy (next.config.js rewrites)
// This avoids CORS and works identically in dev, Docker, and production.
const api = axios.create({ baseURL: '', timeout: 15000 });

api.interceptors.request.use(cfg => {
  if (typeof window !== 'undefined') {
    const t = localStorage.getItem('token');
    if (t) cfg.headers.Authorization = `Bearer ${t}`;
  }
  return cfg;
});
api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem('token'); localStorage.removeItem('user');
    window.location.href = '/login';
  }
  // Log but don't let network errors crash the app overlay
  if (!err.response) {
    console.warn('Network/connection issue on', err.config?.url, '-', err.message);
  }
  return Promise.reject(err);
});

export default api;

export const login = (email: string, password: string) => api.post('/api/auth/login', { email, password });
export const register = (email: string, name: string, password: string) => api.post('/api/auth/register', { email, name, password });
export const getMe = () => api.get('/api/auth/me');

export const onboardTenant = (data: any) => api.post('/api/tenants/onboard', data);
export const getMyTenant = () => api.get('/api/tenants/me');
export const updateTenant = (data: any) => api.patch('/api/tenants/me', data);
export const getFrameworks = () => api.get('/api/tenants/frameworks');
export const getIndustryFrameworks = () => api.get('/api/tenants/industry-frameworks');

export const getConnectorCatalog = () => api.get('/api/connectors/catalog');
export const getConnectors = () => api.get('/api/connectors');
export const addConnector = (data: any) => api.post('/api/connectors', data);
export const triggerScan = (id: number) => api.post(`/api/connectors/${id}/scan`);
export const removeConnector = (id: number) => api.delete(`/api/connectors/${id}`);

export const getDashboard = () => api.get('/api/governance/dashboard');
export const getEvents = (params?: any) => api.get('/api/governance/events', { params });
export const getControls = () => api.get('/api/governance/controls');
export const getFrameworkControls = (framework: string) => api.get('/api/governance/controls', { params: { framework } });
export const getCompliance = () => api.get('/api/governance/compliance');

export const getTickets = (params?: any) => api.get('/api/tickets', { params });
export const createTicket = (event_id: number, due_days?: number) => api.post('/api/tickets', { event_id, due_days: due_days || 30 });
export const getTicket = (id: number) => api.get(`/api/tickets/${id}`);
export const updateTicket = (id: number, data: any) => api.patch(`/api/tickets/${id}`, data);
export const addTicketComment = (id: number, text: string) => api.post(`/api/tickets/${id}/comments`, { text });
export const uploadTicketEvidence = (id: number, file: File, note: string) => {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('note', note || '');
  return api.post(`/api/tickets/${id}/evidence`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
};

export const getAuditReport = () => api.get('/api/auditor/report');
// Pay-as-you-go AI
export const getCredits = () => api.get('/api/ai/credits');
export const purchaseCredits = (amount: number) => api.post('/api/ai/credits/purchase', { amount });
export const getAIUsage = () => api.get('/api/ai/usage');
export const enhanceTicketAI = (id: number) => api.post(`/api/ai/enhance/ticket/${id}`);
export const enhanceAuditSummaryAI = () => api.post('/api/ai/enhance/audit-summary');

// Custom Policies (the 10%)
export const getPolicies = () => api.get('/api/policies');
export const createPolicy = (data: any) => api.post('/api/policies', data);
export const updatePolicy = (id: number, data: any) => api.patch(`/api/policies/${id}`, data);
export const deletePolicy = (id: number) => api.delete(`/api/policies/${id}`);
export const evaluatePolicies = () => api.post('/api/policies/evaluate');
export const bulkUploadPolicies = (file: File) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/api/policies/bulk-upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
};
export const downloadPolicyTemplate = async () => {
  // Fetch through the authenticated client, then trigger a file save.
  const r = await api.get('/api/policies/template', { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([r.data], { type: 'text/csv' }));
  const a = document.createElement('a');
  a.href = url; a.download = 'policy_template.csv'; a.click();
  URL.revokeObjectURL(url);
};

// Report downloads — return blobs
export const downloadAuditPDF = () => api.get('/api/auditor/report/pdf', { responseType: 'blob' });
export const downloadAuditExcel = () => api.get('/api/auditor/report/excel', { responseType: 'blob' });

// ── Platform admin (separate token) ──
const platformApi = axios.create({ baseURL: '', timeout: 15000 });
platformApi.interceptors.request.use(cfg => {
  if (typeof window !== 'undefined') {
    const t = localStorage.getItem('platform_token');
    if (t) cfg.headers.Authorization = `Bearer ${t}`;
  }
  return cfg;
});
export const platformLogin = (email: string, password: string) => platformApi.post('/api/platform/login', { email, password });
export const platformMe = () => platformApi.get('/api/platform/me');
export const platformOverview = () => platformApi.get('/api/platform/overview');
export const platformTenants = () => platformApi.get('/api/platform/tenants');
export const platformTenantDetail = (id: number) => platformApi.get(`/api/platform/tenants/${id}`);
export const platformOnboardTenant = (data: any) => platformApi.post('/api/platform/tenants', data);
export const platformUpdatePlan = (id: number, plan: string) => platformApi.patch(`/api/platform/tenants/${id}/plan`, { plan });
export const platformUpdateStatus = (id: number, status: string) => platformApi.patch(`/api/platform/tenants/${id}/status`, { status });
// Platform email/SMTP config + editable tenant info
export const platformGetEmailSettings = () => platformApi.get('/api/platform/settings/email');
export const platformUpdateEmailSettings = (data: any) => platformApi.patch('/api/platform/settings/email', data);
export const platformTestEmail = (to_address: string) => platformApi.post('/api/platform/settings/email/test', { to_address });
export const platformEditTenantInfo = (id: number, data: any) => platformApi.patch(`/api/platform/tenants/${id}/info`, data);
export const platformDeleteTenant = (id: number) => platformApi.delete(`/api/platform/tenants/${id}`);
export const platformImpersonate = (id: number) => platformApi.post(`/api/platform/tenants/${id}/impersonate`);

// ── SOC 2 readiness ──
export const getSoc2Criteria = (categories?: string) => api.get('/api/soc2/criteria', { params: { categories } });
export const setupSoc2 = (data: any) => api.post('/api/soc2/setup', data);
export const getSoc2Readiness = () => api.get('/api/soc2/readiness');
export const updateSoc2Criterion = (id: string, data: any) => api.patch(`/api/soc2/criterion/${id}`, data);

// ── Evidence & attestation ──
export const listEvidence = (params?: any) => api.get('/api/evidence', { params });
export const uploadEvidenceDoc = (formData: FormData) => api.post('/api/evidence/document', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const createAttestation = (data: any) => api.post('/api/evidence/attestation', data);
export const deleteEvidence = (id: number) => api.delete(`/api/evidence/${id}`);
export const getControlStatuses = (framework: string) => api.get(`/api/evidence/controls/${framework}`);
export const updateControlStatus = (framework: string, controlId: string, data: any) => api.patch(`/api/evidence/controls/${framework}/${controlId}`, data);
export const getCoverage = (framework: string) => api.get(`/api/evidence/coverage/${framework}`);

// ── Tenant user management ──
export const listTenantUsers = () => api.get('/api/users');
export const addTenantUser = (data: any) => api.post('/api/users', data);
export const updateTenantUserRole = (id: number, role: string) => api.patch(`/api/users/${id}`, { role });
export const removeTenantUser = (id: number) => api.delete(`/api/users/${id}`);

// ── Platform team management ──
export const platformListTeam = () => platformApi.get('/api/platform/team');
export const platformAddTeam = (data: any) => platformApi.post('/api/platform/team', data);
export const platformUpdateTeamRole = (id: number, role: string) => platformApi.patch(`/api/platform/team/${id}`, { role });
export const platformRemoveTeam = (id: number) => platformApi.delete(`/api/platform/team/${id}`);

// ── Collectors (CCE) — tenant view ──
export const listCollectors = () => api.get('/api/collectors');
export const listAgents = () => api.get('/api/collectors/agents');
export const scanNow = (data: any) => api.post('/api/collectors/scan-now', data);
export const listScanJobs = () => api.get('/api/collectors/jobs');

export const registerCollector = (data: any) => api.post('/api/collectors/register', data);
export const deleteCollector = (id: number) => api.delete(`/api/collectors/${id}`);

// ── Scheduler / asset groups ──
export const listGroups = () => api.get('/api/scheduler');
export const createGroup = (data: any) => api.post('/api/scheduler', data);
export const updateGroup = (id: number, data: any) => api.patch(`/api/scheduler/${id}`, data);
export const deleteGroup = (id: number) => api.delete(`/api/scheduler/${id}`);
export const scanGroup = (id: number) => api.post(`/api/scheduler/${id}/scan`);

// ── Framework & control management ──
export const listFrameworksAdmin = () => api.get('/api/frameworks');
export const getFrameworkControlsAdmin = (fwId: number) => api.get(`/api/frameworks/${fwId}/controls`);
export const createFrameworkAdmin = (data: any) => api.post('/api/frameworks', data);
export const deleteFrameworkAdmin = (fwId: number) => api.delete(`/api/frameworks/${fwId}`);
export const addControl = (fwId: number, data: any) => api.post(`/api/frameworks/${fwId}/controls`, data);
export const editControl = (controlPk: number, data: any) => api.patch(`/api/frameworks/controls/${controlPk}`, data);
export const deleteControl = (controlPk: number) => api.delete(`/api/frameworks/controls/${controlPk}`);
export const bulkUploadControls = (fwId: number, file: File, replaceExisting = false) => {
  const fd = new FormData(); fd.append('file', file);
  return api.post(`/api/frameworks/${fwId}/controls/bulk-upload?replace_existing=${replaceExisting}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
};
export const downloadControlsTemplate = async () => {
  const r = await api.get('/api/frameworks/controls-template', { responseType: 'blob' });
  const url = URL.createObjectURL(new Blob([r.data], { type: 'text/csv' }));
  const a = document.createElement('a'); a.href = url; a.download = 'controls_template.csv'; a.click();
  URL.revokeObjectURL(url);
};

// ── Devices (on-prem network devices) ──
export const listDevices = () => api.get('/api/devices');
export const deviceCatalog = () => api.get('/api/devices/catalog');
export const createDevice = (data: any) => api.post('/api/devices', data);
export const updateDevice = (id: number, data: any) => api.patch(`/api/devices/${id}`, data);
export const deleteDevice = (id: number) => api.delete(`/api/devices/${id}`);
export const scanDevice = (id: number) => api.post(`/api/devices/${id}/scan`);

// ── Collectors (CCE) — platform/operator view ──
export const platformListAllCollectors = () => platformApi.get('/api/collectors/platform/all');
export const platformRegisterCollector = (data: any) => platformApi.post('/api/collectors/platform/register', data);

// ── Cody AI assistant ──
export const askCody = (message: string, history: any[]) => api.post('/api/cody/chat', { message, history });
