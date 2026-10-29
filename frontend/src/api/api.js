const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// Demo mode: when token is 'demo-preview-token', skip all API calls
export function isDemoMode() {
  return localStorage.getItem('token') === 'demo-preview-token';
}

// Mock data returned in demo mode so dashboards render without a backend
function getDemoData(endpoint, method) {
  if (method !== 'GET') {
    return Promise.resolve({ success: true, message: 'Demo mode — action simulated' });
  }
  if (endpoint.includes('/batches') && !endpoint.match(/\/batches\/\d/)) {
    return Promise.resolve([
      {
        id: 1,
        name: 'Batch 2024-A (Demo)',
        status: 'approved',
        student_count: 142,
        institute_id: 1,
        institute_name: 'L M Thapar School Of Management',
        created_at: '2024-11-01T10:00:00',
        pushed_at: '2024-11-03T10:00:00',
      },
      {
        id: 2,
        name: 'Batch 2024-B (Demo)',
        status: 'under_review',
        student_count: 98,
        institute_id: 1,
        institute_name: 'L M Thapar School Of Management',
        created_at: '2024-11-10T10:00:00',
        pushed_at: '2024-11-12T10:00:00',
      },
    ]);
  }
  if (endpoint.match(/\/batches\/\d+$/) || endpoint.match(/\/batches\/\d+\/last-run/)) {
    return Promise.resolve({
      id: 1,
      name: 'Batch 2024-A (Demo)',
      status: 'approved',
      student_count: 142,
      students: [
        { id: 1, apaar_id: '123456789012', full_name: 'Aarav Mehta', status: 'verified', correction_status: null },
        { id: 2, apaar_id: '234567890123', full_name: 'Priya Sharma', status: 'verified', correction_status: null },
        { id: 3, apaar_id: '345678901234', full_name: 'Rahul Verma', status: 'mismatch', correction_status: 'pending' },
      ],
      verification_result: {
        id: 1,
        status: 'completed',
        pass_count: 130,
        fail_count: 8,
        mismatch_count: 4,
        run_at: '2024-11-03T11:00:00',
        reviewer_decision: 'approved',
        reviewer_note: 'All records verified. Minor mismatches resolved.',
      },
    });
  }
  if (endpoint.includes('/institutes/list')) {
    return Promise.resolve([
      { id: 1, name: 'L M Thapar School Of Management', code: 'LMTSM', status: 'active' },
      { id: 2, name: 'IIT Delhi', code: 'IITD', status: 'active' },
    ]);
  }
  if (endpoint.includes('/email/status')) {
    return Promise.resolve({ configured: true, provider: 'Demo SMTP', from: 'vishwas@demo.in' });
  }
  if (endpoint.includes('/audit/verify-chain')) {
    return Promise.resolve({ valid: true, blocks: 3, message: 'Audit chain intact (Demo)' });
  }
  // Default empty response
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
    return getDemoData(endpoint, options.method || 'GET');
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
  uploadStudents: (formData) => apiRequest('/student/upload', { method: 'POST', body: formData }),
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
