// Shell — Enterprise AI Firewall — API Client

const API_BASE = '';

function getToken() {
  // localStorage persists across page loads/redirects; sessionStorage does not
  return localStorage.getItem('fw_token') || sessionStorage.getItem('fw_token');
}

function getUser() {
  try {
    const u = localStorage.getItem('fw_user') || sessionStorage.getItem('fw_user');
    return u ? JSON.parse(u) : null;
  } catch { return null; }
}

function setAuth(token, user) {
  // Save to localStorage so token survives page redirects
  localStorage.setItem('fw_token', token);
  localStorage.setItem('fw_user', JSON.stringify(user));
  sessionStorage.setItem('fw_token', token);
  sessionStorage.setItem('fw_user', JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem('fw_token');
  localStorage.removeItem('fw_user');
  sessionStorage.removeItem('fw_token');
  sessionStorage.removeItem('fw_user');
}

function requireAuth() {
  const token = getToken();
  if (!token || token === 'null' || token === 'undefined' || token === '') {
    window.location.replace('/index.html');
    return false;
  }
  return true;
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  try {
    const res = await fetch(API_BASE + path, { ...options, headers });
    if (res.status === 401) {
      clearAuth();
      window.location.replace('/index.html');
      return null;
    }
    return await res.json();
  } catch (e) {
    console.error('[FIREWALL][API] Error:', e);
    return null;
  }
}

const API = {
  async login(username, password) {
    return apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
  },

  async sendChat(prompt, sessionId) {
    return apiFetch('/api/chat/send', {
      method: 'POST',
      body: JSON.stringify({ prompt, session_id: sessionId })
    });
  },

  async getDashboardStats() {
    return apiFetch('/api/dashboard/stats');
  },

  async getActionQueue() {
    return apiFetch('/api/actions/queue');
  },

  async approveAction(id) {
    return apiFetch(`/api/actions/approve/${id}`, { method: 'POST' });
  },

  async rejectAction(id) {
    return apiFetch(`/api/actions/reject/${id}`, { method: 'POST' });
  },

  async delegateToHR(id) {
    return apiFetch(`/api/actions/delegate/${id}`, { method: 'POST' });
  },

  async scanShadowText(text) {
    return apiFetch('/api/shadow/scan-text', {
      method: 'POST',
      body: JSON.stringify({ text })
    });
  },

  async scanPrompt(text) {
    return apiFetch('/api/scan/prompt', {
      method: 'POST',
      body: JSON.stringify({ text })
    });
  },

  async scanPDF(formData) {
    const token = getToken();
    try {
      const res = await fetch(API_BASE + '/api/shadow/scan-pdf', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (res.status === 401) {
        clearAuth();
        window.location.replace('/index.html');
        return null;
      }
      return await res.json();
    } catch (e) {
      console.error('[FIREWALL][API] PDF scan error:', e);
      return null;
    }
  },

  async getAlerts() {
    return apiFetch('/api/alerts/unread');
  }
};

// ── Auth Guard for protected pages ──────────────────────────────────────
function initPage(pageName) {
  if (!requireAuth()) return null;

  const user = getUser();
  if (!user) {
    clearAuth();
    window.location.replace('/index.html');
    return null;
  }

  // Set user pill in sidebar
  const userPill = document.getElementById('user-pill-name');
  if (userPill) userPill.textContent = user.username;
  const userAvatar = document.getElementById('user-avatar');
  if (userAvatar) userAvatar.textContent = user.username[0].toUpperCase();
  const userRole = document.getElementById('user-role');
  if (userRole) userRole.textContent = user.role;

  // Logout buttons
  document.querySelectorAll('.logout-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      clearAuth();
      window.location.replace('/index.html');
    });
  });

  // Alert bell count
  loadAlertCount();

  console.log(`[FIREWALL][${pageName}] Page initialized for user: ${user.username} (${user.role})`);
  return user;
}

async function loadAlertCount() {
  const resp = await API.getAlerts();
  if (resp && resp.success) {
    const count = resp.data.count;
    const badge = document.getElementById('alert-count');
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? 'flex' : 'none';
    }
  }
}

// ── Count-up animation ──────────────────────────────────────────────────
function animateCountUp(el, target, duration = 800) {
  if (!el) return;
  const start = performance.now();
  function update(time) {
    const progress = Math.min((time - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(target * eased);
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}