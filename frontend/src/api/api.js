const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// Demo mode: when token is 'demo-preview-token', skip all API calls
export function isDemoMode() {
  return localStorage.getItem('token') === 'demo-preview-token';
}

// ─── DEMO STATE ENGINE ────────────────────────────────────────────────────────
// All demo data lives in localStorage under 'vishwas_demo_state'.
// Both portals share this state — institute pushes, AICTE sees it.

const DEMO_KEY = 'vishwas_demo_state';

function demoGetState() {
  try {
    const raw = localStorage.getItem(DEMO_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) {}
  return { batches: [], pendingStudents: [] };
}

function demoSaveState(state) {
  localStorage.setItem(DEMO_KEY, JSON.stringify(state));
}

// Parse CSV text → array of student row objects
function parseCsvStudents(csvText) {
  const lines = csvText.trim().split(/\r?\n/);
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/"/g, ''));
  return lines.slice(1).map((line, i) => {
    const vals = line.split(',').map(v => v.trim().replace(/"/g, ''));
    const row = {};
    headers.forEach((h, idx) => { row[h] = vals[idx] || ''; });
    // normalise common column aliases
    const apaar = row['apaar_id'] || row['apaarid'] || row['apaar'] || '';
    const name  = row['name'] || row['full_name'] || row['student_name'] || `Student ${i + 1}`;
    const prog  = row['program'] || row['programme'] || row['course'] || 'B.Tech';
    const yr    = row['enrollment_year'] || row['year'] || '2022';
    const email = row['email'] || row['email_id'] || '';
    return {
      student_id: Date.now() + i,
      apaar_id_masked: apaar ? `****${apaar.slice(-4)}` : '****DEMO',
      name: name,
      program: prog,
      enrollment_year: yr,
      email: email,
      verification_status: 'pending',
      verification_status_label: 'Pending',
      email_status: 'skipped',
      email_status_label: 'Skipped (Demo)',
      corrections: null,
    };
  }).filter(s => s.name);
}

// Upload students → store in pending pool
export function demoUploadStudents(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const students = parseCsvStudents(text);
      if (students.length === 0) {
        reject(new Error('No valid rows found in CSV. Check your columns: apaar_id, name, program, enrollment_year, email'));
        return;
      }
      const state = demoGetState();
      state.pendingStudents = students;
      demoSaveState(state);
      resolve({ inserted: students.length, rejected: 0 });
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}

// Mock data returned in demo mode so dashboards render without a backend
function getDemoData(endpoint, method, body) {
  const state = demoGetState();

  // ── POST / mutating actions ──────────────────────────────────────────────
  if (method === 'POST') {
    // Create batch
    if (endpoint === '/batches') {
      const batchName = (body && body.name) ? body.name : `Demo Batch ${state.batches.length + 1}`;
      const students = (state.pendingStudents || []).slice(); // take uploaded students
      const newBatch = {
        batch_id: Date.now(),
        name: batchName,
        status: 'draft',
        status_label: 'Draft',
        student_count: students.length,
        institute_id: 1,
        institute_name: localStorage.getItem('institute_name') || 'Demo Institute',
        created_at: new Date().toISOString(),
        pushed_at: null,
        students: students,
        verification_result: null,
        reject_reason: null,
      };
      state.batches.push(newBatch);
      state.pendingStudents = [];
      demoSaveState(state);
      return Promise.resolve({ batch_id: newBatch.batch_id, name: newBatch.name, student_count: newBatch.student_count });
    }

    // Push batch to AICTE
    const pushMatch = endpoint.match(/\/batches\/(\d+)\/push/);
    if (pushMatch) {
      const bId = Number(pushMatch[1]);
      const batch = state.batches.find(b => b.batch_id === bId);
      if (batch) {
        batch.status = 'under_review';
        batch.status_label = 'Under Review';
        batch.pushed_at = new Date().toISOString();
        // Auto-generate a verification result for AICTE to see
        batch.verification_result = {
          id: Date.now(),
          status: 'completed',
          pass_count: Math.max(1, batch.student_count - 2),
          fail_count: 1,
          mismatch_count: 1,
          run_at: new Date().toISOString(),
          reviewer_decision: null,
          reviewer_note: null,
        };
        // Mark some students verified for display
        batch.students = batch.students.map((s, i) => ({
          ...s,
          verification_status: i < batch.students.length - 1 ? 'verified' : 'mismatch',
          verification_status_label: i < batch.students.length - 1 ? 'Verified' : 'Mismatch',
        }));
        demoSaveState(state);
      }
      return Promise.resolve({ success: true });
    }

    // AICTE approve batch
    const approveMatch = endpoint.match(/\/aicte\/batches\/(\d+)\/approve/);
    if (approveMatch) {
      const bId = Number(approveMatch[1]);
      const batch = state.batches.find(b => b.batch_id === bId);
      if (batch) {
        batch.status = 'approved';
        batch.status_label = 'Approved';
        if (batch.verification_result) {
          batch.verification_result.reviewer_decision = 'approved';
          batch.verification_result.reviewer_note = 'Approved via demo review.';
        }
        demoSaveState(state);
      }
      return Promise.resolve({ success: true });
    }

    // AICTE reject batch
    const rejectMatch = endpoint.match(/\/aicte\/batches\/(\d+)\/reject/);
    if (rejectMatch) {
      const bId = Number(rejectMatch[1]);
      const batch = state.batches.find(b => b.batch_id === bId);
      if (batch) {
        batch.status = 'returned';
        batch.status_label = 'Returned';
        batch.reject_reason = (body && body.reason) ? body.reason : 'Returned for revision.';
        demoSaveState(state);
      }
      return Promise.resolve({ success: true });
    }

    // Verifications / other POST → simulate silently
    return Promise.resolve({ success: true, sent_count: 0, message: 'Demo mode — email skipped (would send in live system)' });
  }

  // ── GET requests ─────────────────────────────────────────────────────────
  // List batches (institute sees draft+; AICTE sees under_review+)
  if (endpoint === '/batches') {
    const role = localStorage.getItem('role') || '';
    const aicteStatuses = ['under_review', 'approved', 'returned', 'pushed'];
    const filtered = role === 'aicte_admin'
      ? state.batches.filter(b => aicteStatuses.includes(b.status))
      : state.batches;
    return Promise.resolve({ batches: filtered });
  }

  // Single batch details
  const batchDetailMatch = endpoint.match(/\/batches\/(\d+)$/);
  if (batchDetailMatch) {
    const bId = Number(batchDetailMatch[1]);
    const batch = state.batches.find(b => b.batch_id === bId);
    return Promise.resolve(batch || {});
  }

  // Last run (AICTE verification run panel)
  const lastRunMatch = endpoint.match(/\/aicte\/batches\/(\d+)\/last-run/);
  if (lastRunMatch) {
    const bId = Number(lastRunMatch[1]);
    const batch = state.batches.find(b => b.batch_id === bId);
    return Promise.resolve(batch?.verification_result || null);
  }

  if (endpoint.includes('/institutes/list')) {
    return Promise.resolve([
      { id: 1, name: 'L M Thapar School Of Management', code: 'LMTSM', status: 'active' },
      { id: 2, name: 'IIT Delhi', code: 'IITD', status: 'active' },
    ]);
  }
  if (endpoint.includes('/email/status')) {
    return Promise.resolve({ configured: false, can_send: false, provider: 'Demo — email skipped', from: '' });
  }
  if (endpoint.includes('/audit/verify-chain')) {
    return Promise.resolve({ valid: true, blocks: state.batches.length + 1, message: 'Audit chain intact (Demo)' });
  }

  return Promise.resolve({});
}

export function getAuthToken() {
  return localStorage.getItem('token');
}

export function setAuthSession(token, role, instituteId = null, email = '', fullName = '', instituteName = '') {
  localStorage.setItem('token', token);
  localStorage.setItem('role', role);
  localStorage.setItem('email', email);
  localStorage.setItem('full_name', fullName);
  if (instituteId !== null) {
    localStorage.setItem('institute_id', String(instituteId));
    localStorage.setItem('institute_name', instituteName || '');
  } else {
    localStorage.removeItem('institute_id');
    localStorage.removeItem('institute_name');
  }
}

export function clearAuthSession() {
  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('institute_id');
  localStorage.removeItem('institute_name');
  localStorage.removeItem('email');
  localStorage.removeItem('full_name');
}

export function getCurrentUser() {
  const token = localStorage.getItem('token');
  if (!token) return null;
  return {
    token,
    role: localStorage.getItem('role') || '',
    institute_id: localStorage.getItem('institute_id') ? parseInt(localStorage.getItem('institute_id'), 10) : null,
    institute_name: localStorage.getItem('institute_name') || '',
    email: localStorage.getItem('email') || '',
    full_name: localStorage.getItem('full_name') || '',
  };
}

// Public request — never sends Authorization header (used for student-facing verify endpoints)
export async function publicApiRequest(endpoint, options = {}) {
  const headers = { ...options.headers };

  let body = options.body;
  if (body && !(body instanceof FormData) && typeof body === 'object') {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }

  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, { ...options, headers, body });

    const contentType = response.headers.get('content-type') || '';
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = data.detail || data.message || `Request failed with status ${response.status}`;
      const error = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (err) {
    console.error(`Public API Error on [${options.method || 'GET'}] ${endpoint}:`, err);
    throw err;
  }
}

export async function apiRequest(endpoint, options = {}) {
  // --- DEMO MODE: skip backend, return mock data ---
  if (isDemoMode()) {
    return getDemoData(endpoint, options.method || 'GET', options.body || null);
  }
  // --- END DEMO MODE ---

  const token = getAuthToken();
  const headers = { ...options.headers };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let body = options.body;
  if (body && !(body instanceof FormData) && typeof body === 'object') {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }

  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, { ...options, headers, body });

    if (response.status === 401) {
      clearAuthSession();
      const base = import.meta.env.BASE_URL || '/';
      const loginPath = base.endsWith('/') ? `${base}login` : `${base}/login`;
      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/verify/')) {
        window.location.href = `${loginPath}?session_expired=true`;
      }
      throw new Error('Session expired or unauthorized');
    }

    if (response.status === 403) {
      const errJson = await response.json().catch(() => ({}));
      throw new Error(errJson.detail || 'Access forbidden: Insufficient permissions for this action');
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/pdf') || options.responseType === 'blob') {
      if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
      return await response.blob();
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = data.detail || data.message || `Request failed with status ${response.status}`;
      const error = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (err) {
    console.error(`API Error on [${options.method || 'GET'}] ${endpoint}:`, err);
    throw err;
  }
}

export const authApi = {
  login: async (email, password) => {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    setAuthSession(data.access_token, data.role, data.institute_id, data.email, data.full_name, data.institute_name);
    return data;
  },
  logout: () => {
    clearAuthSession();
  },
  getInstitutesList: () => apiRequest('/institutes/list'),
};

export const instituteApi = {
  uploadStudents: (formData) => {
    if (isDemoMode()) { const file = formData.get('file'); return demoUploadStudents(file); }
    return apiRequest('/student/upload', { method: 'POST', body: formData });
  },
  createBatch: (name) => apiRequest('/batches', { method: 'POST', body: { name } }),
  getBatches: () => apiRequest('/batches'),
  getBatchDetails: (batchId) => apiRequest(`/batches/${batchId}`),
  pushBatch: (batchId) => apiRequest(`/batches/${batchId}/push`, { method: 'POST' }),
  sendVerifications: (batchId) => apiRequest(`/batches/${batchId}/send-verifications`, { method: 'POST' }),
  reviewCorrection: (batchId, studentId, action, note) =>
    apiRequest(`/batches/${batchId}/students/${studentId}/review-correction`, {
      method: 'POST',
      body: { action, note },
    }),
  downloadReport: (batchId) => apiRequest(`/batches/${batchId}/report`, { method: 'GET', responseType: 'blob' }),
  notifyStudents: (batchId) => apiRequest(`/batches/${batchId}/notify-approved-students`, { method: 'POST' }),
  getEmailStatus: () => apiRequest('/email/status'),
  sendTestEmail: (email) => apiRequest('/email/test', { method: 'POST', body: { email } }),
};

export const aicteApi = {
  getBatches: () => apiRequest('/batches'),
  getBatchDetails: (batchId) => apiRequest(`/batches/${batchId}`),
  getLastRun: (batchId) => apiRequest(`/aicte/batches/${batchId}/last-run`),
  submitReviewerDecision: (resultId, decision, note) =>
    apiRequest(`/aicte/verification-results/${resultId}/decision`, {
      method: 'POST',
      body: { decision, note },
    }),
  approveBatch: (batchId) => apiRequest(`/aicte/batches/${batchId}/approve`, { method: 'POST' }),
  rejectBatch: (batchId, reason) => apiRequest(`/aicte/batches/${batchId}/reject`, { method: 'POST', body: { reason } }),
  onboardInstitute: (institute_id, admin_email, admin_name, admin_password) =>
    apiRequest('/aicte/onboard-institute', {
      method: 'POST',
      body: { institute_id, admin_email, admin_name, admin_password },
    }),
  getInstitutesList: () => apiRequest('/institutes/list'),
  verifyChain: () => apiRequest('/audit/verify-chain'),
  getEmailStatus: () => apiRequest('/email/status'),
  sendTestEmail: (email) => apiRequest('/email/test', { method: 'POST', body: { email } }),
};

export const publicApi = {
  // These three MUST NOT send any auth header — token-only public endpoints
  getVerificationPayload: (token) => publicApiRequest(`/verify/token/${token}`),
  confirmVerification: (token, otp = '') => publicApiRequest(`/verify/token/${token}/confirm`, { method: 'POST', body: { otp } }),
  submitCorrection: (token, corrections, otp = '') => publicApiRequest(`/verify/token/${token}/correct`, { method: 'POST', body: { corrections, otp } }),
  // Document verifier is public too
  getPublicKey: () => publicApiRequest('/verify/public-key'),
  verifyDocument: (document, signature) => publicApiRequest('/verify/document', { method: 'POST', body: { document, signature } }),
  getDocumentByApaar: (apaarId) => publicApiRequest(`/verify/document/${apaarId}`),
};

