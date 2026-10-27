const API_BASE = import.meta.env.VITE_API_URL || '/api';

export function getAuthToken() {
  return localStorage.getItem('token');
}

export function setAuthSession(token, role, instituteId = null, username = '') {
  localStorage.setItem('token', token);
  localStorage.setItem('role', role);
  if (instituteId !== null) {
    localStorage.setItem('institute_id', String(instituteId));
  } else {
    localStorage.removeItem('institute_id');
  }
  localStorage.setItem('username', username);
}

export function clearAuthSession() {
  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('institute_id');
  localStorage.removeItem('username');
}

export function getCurrentUser() {
  const token = localStorage.getItem('token');
  if (!token) return null;
  return {
    token,
    role: localStorage.getItem('role') || '',
    institute_id: localStorage.getItem('institute_id') ? parseInt(localStorage.getItem('institute_id'), 10) : null,
    username: localStorage.getItem('username') || '',
  };
}

export async function apiRequest(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    ...options.headers,
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // If body is not FormData and not explicitly Content-Type set, format JSON
  let body = options.body;
  if (body && !(body instanceof FormData) && typeof body === 'object') {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }

  const url = `${API_BASE}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      body,
    });

    if (response.status === 401) {
      clearAuthSession();
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/verify/')) {
        window.location.href = '/login?session_expired=true';
      }
      throw new Error('Session expired or unauthorized');
    }

    if (response.status === 403) {
      throw new Error('Access forbidden: Insufficient permissions for this action');
    }

    // Check if binary download (e.g. PDF)
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/pdf') || options.responseType === 'blob') {
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
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

// ── Auth APIs ──────────────────────────────────────────────
export const authApi = {
  login: async (username, role, institute_id = null) => {
    const data = await apiRequest('/auth/token', {
      method: 'POST',
      body: { username, role, institute_id },
    });
    setAuthSession(data.access_token, data.role, institute_id, username);
    return data;
  },
  logout: () => {
    clearAuthSession();
  },
  getInstitutesList: () => apiRequest('/institutes/list'),
};

// ── Institute APIs ─────────────────────────────────────────
export const instituteApi = {
  uploadStudents: (formData) => apiRequest('/student/upload', { method: 'POST', body: formData }),
  getCapacity: (instituteId, program = 'ALL') => apiRequest(`/dashboard/capacity/${instituteId}?program=${encodeURIComponent(program)}`),
  createBatch: (name, institute_id) => apiRequest('/batches', { method: 'POST', body: { name, institute_id } }),
  getBatches: () => apiRequest('/batches'),
  getBatchDetails: (batchId) => apiRequest(`/batches/${batchId}`),
  addStudentsToBatch: (batchId, studentIds) => apiRequest(`/batches/${batchId}/students`, { method: 'POST', body: { student_ids: studentIds } }),
  pushBatch: (batchId) => apiRequest(`/batches/${batchId}/push`, { method: 'POST' }),
  generateTokens: (batchId) => apiRequest(`/batches/${batchId}/verification/generate`, { method: 'POST' }),
  sendVerificationEmails: (batchId) => apiRequest(`/batches/${batchId}/verification/send-emails`, { method: 'POST' }),
  getVerificationStatus: (batchId) => apiRequest(`/batches/${batchId}/verification/status`),
  markUnresponsive: (batchId) => apiRequest(`/batches/${batchId}/verification/mark-unresponsive`, { method: 'POST' }),
  resendToken: (batchId, studentId) => apiRequest(`/batches/${batchId}/verification/${studentId}/resend`, { method: 'POST' }),
  downloadReport: (batchId) => apiRequest(`/batches/${batchId}/report`, { method: 'GET', responseType: 'blob' }),
  notifyStudents: (batchId) => apiRequest(`/batches/${batchId}/notify`, { method: 'POST' }),
};

// ── AICTE APIs ─────────────────────────────────────────────
export const aicteApi = {
  getTrustScores: () => apiRequest('/dashboard/trust-scores'),
  recomputeTrustScore: (instituteId) => apiRequest(`/dashboard/trust-scores/${instituteId}/recompute`, { method: 'POST' }),
  getFlaggedRecords: (status = 'open') => apiRequest(`/dashboard/flagged?status=${status}`),
  reviewFlag: (flagId, notes = '') => apiRequest(`/dashboard/flagged/${flagId}/review`, { method: 'POST', body: { status: 'reviewed', notes } }),
  getDuplicates: () => apiRequest('/dashboard/duplicates'),
  getBatches: () => apiRequest('/batches'),
  getBatchDetails: (batchId) => apiRequest(`/batches/${batchId}`),
  approveBatch: (batchId) => apiRequest(`/aicte/batches/${batchId}/approve`, { method: 'POST' }),
  rejectBatch: (batchId, reason) => apiRequest(`/aicte/batches/${batchId}/reject`, { method: 'POST', body: { reason } }),
  verifyChain: () => apiRequest('/audit/verify-chain'),
  createCheckpoint: () => apiRequest('/security/checkpoint', { method: 'POST' }),
  verifyAnchored: () => apiRequest('/security/verify-anchored'),
  getHoneytokensStatus: () => apiRequest('/security/honeytokens/status'),
  getEmailLogs: (batchId = null) => apiRequest(batchId ? `/emails/log?batch_id=${batchId}` : '/emails/log'),
  getEmailConfig: () => apiRequest('/emails/config'),
};

// ── Public Verification APIs ───────────────────────────────
export const publicApi = {
  getPublicKey: () => apiRequest('/verify/public-key'),
  verifyDocument: (document, signature) => apiRequest('/verify/document', { method: 'POST', body: { document, signature } }),
  getDocumentByApaar: (apaarId) => apiRequest(`/verify/document/${apaarId}`),
  getTokenDetails: (token) => apiRequest(`/verify/token/${token}`),
  confirmToken: (token) => apiRequest(`/verify/token/${token}/confirm`, { method: 'POST' }),
  correctToken: (token, corrections) => apiRequest(`/verify/token/${token}/correct`, { method: 'POST', body: { corrections } }),
};

