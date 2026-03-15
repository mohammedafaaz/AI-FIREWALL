// Shell — Enterprise AI Firewall — Dashboard JS

let doughnutChart, lineChart, barChart;
let isFirstLoad = true;
let allEvents = [];
let currentUserRole = '';
let showDetailedView = false;
let dailyData = [];
let hourlyData = [];

async function loadDashboard() {
  console.log('[FIREWALL][DASHBOARD] Loading dashboard data...');
  const resp = await API.getDashboardStats();
  console.log('[FIREWALL][DASHBOARD] API Response:', resp);
  
  if (!resp || !resp.success) {
    console.error('[FIREWALL][DASHBOARD] Failed to load dashboard data');
    return;
  }

  const d = resp.data;
  currentUserRole = d.user_role || 'employee';
  console.log('[FIREWALL][DASHBOARD] User role:', currentUserRole);

  // ── Stats Cards ──────────────────────────────────────────────────────
  if (isFirstLoad) {
    animateCountUp(document.getElementById('stat-total'), d.total_threats || 0);
    animateCountUp(document.getElementById('stat-blocked'), d.blocked_today || 0);
    animateCountUp(document.getElementById('stat-sessions'), d.active_sessions || 0);
    animateCountUp(document.getElementById('stat-pending'), d.pending_approvals || 0);
    isFirstLoad = false;
  } else {
    document.getElementById('stat-total').textContent = d.total_threats || 0;
    document.getElementById('stat-blocked').textContent = d.blocked_today || 0;
    document.getElementById('stat-sessions').textContent = d.active_sessions || 0;
    document.getElementById('stat-pending').textContent = d.pending_approvals || 0;
  }

  // Risk level
  const riskEl = document.getElementById('stat-risk');
  if (riskEl) {
    riskEl.innerHTML = `<span class="risk-badge risk-${d.risk_level}">${d.risk_level}</span>`;
  }

  // Personal risk level for admin/hr
  if (currentUserRole === 'admin' || currentUserRole === 'hr') {
    const personalRiskCard = document.getElementById('personal-risk-card');
    if (personalRiskCard) personalRiskCard.style.display = 'block';
    
    const personalRiskEl = document.getElementById('stat-personal-risk');
    if (personalRiskEl && d.personal_risk_level) {
      personalRiskEl.innerHTML = `<span class="risk-badge risk-${d.personal_risk_level}">${d.personal_risk_level}</span>`;
    }
  }

  // Alert count
  const alertBadge = document.getElementById('alert-count');
  if (alertBadge) {
    const count = d.unread_alerts_count || 0;
    alertBadge.textContent = count;
    alertBadge.style.display = count > 0 ? 'flex' : 'none';
  }

  // Show/hide search bar and top threat section based on role
  const searchBar = document.getElementById('user-search');
  const topThreatSection = document.getElementById('top-threat-section');
  if (currentUserRole === 'admin' || currentUserRole === 'hr') {
    if (searchBar) searchBar.style.display = 'block';
    if (topThreatSection) topThreatSection.style.display = 'block';
    renderTopThreatUsers(d.top_threat_users || []);
  } else {
    if (searchBar) searchBar.style.display = 'none';
    if (topThreatSection) topThreatSection.style.display = 'none';
  }

  // ── Doughnut Chart ───────────────────────────────────────────────────
  const typeData = d.threats_by_type || [];
  const donutLabels = typeData.map(t => t.module);
  const donutValues = typeData.map(t => t.cnt);
  const donutColors = donutLabels.map(l => moduleColor(l));
  const total = donutValues.reduce((a, b) => a + b, 0);

  if (doughnutChart) {
    doughnutChart.data.labels = donutLabels;
    doughnutChart.data.datasets[0].data = donutValues;
    doughnutChart.data.datasets[0].backgroundColor = donutColors;
    doughnutChart.update();
  } else {
    const ctx = document.getElementById('doughnut-chart');
    if (ctx) {
      // Set default text color for Chart.js
      Chart.defaults.color = '#ffffff';
      
      doughnutChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: donutLabels.length ? donutLabels : ['No Data'],
          datasets: [{
            data: donutValues.length ? donutValues : [1],
            backgroundColor: donutColors.length ? donutColors : ['rgba(0,0,0,0.08)'],
            borderWidth: 2,
            borderColor: 'rgba(255, 255, 255, 0)',
            hoverBorderWidth: 3
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { 
              position: 'bottom', 
              labels: { 
                padding: 16, 
                font: { size: 12, weight: '600' },
                color: '#ffffff',
                generateLabels: (chart) => {
                  const data = chart.data;
                  return data.labels.map((label, i) => {
                    const value = data.datasets[0].data[i];
                    const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                    return {
                      text: `${label}: ${value} (${percent}%)`,
                      fillStyle: data.datasets[0].backgroundColor[i],
                      hidden: false,
                      index: i
                    };
                  });
                }
              }
            },
            tooltip: {
              backgroundColor: 'rgba(13, 17, 23, 0.95)',
              titleColor: '#e2eaf4',
              bodyColor: '#e2eaf4',
              borderColor: '#1e2d3d',
              borderWidth: 1,
              callbacks: {
                label: (context) => {
                  const value = context.parsed;
                  const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                  return `${context.label}: ${value} (${percent}%)`;
                }
              }
            }
          },
          cutout: '68%'
        }
      });
    }
  }

  // ── Line Chart ───────────────────────────────────────────────────────
  hourlyData = d.threats_hourly || [];
  dailyData = d.threats_daily || [];
  updateLineChart();

  // ── Bar Chart ────────────────────────────────────────────────────────
  const moduleData = d.threats_per_module || [];
  const barLabels = moduleData.map(m => m.module);
  const barValues = moduleData.map(m => m.cnt);
  const barColors = barLabels.map(l => moduleColor(l));

  if (barChart) {
    barChart.data.labels = barLabels;
    barChart.data.datasets[0].data = barValues;
    barChart.data.datasets[0].backgroundColor = barColors;
    barChart.update();
  } else {
    const ctx3 = document.getElementById('bar-chart');
    if (ctx3) {
      barChart = new Chart(ctx3, {
        type: 'bar',
        data: {
          labels: barLabels.length ? barLabels : ['No Data'],
          datasets: [{
            label: 'Blocked Threats',
            data: barValues.length ? barValues : [0],
            backgroundColor: barColors.length ? barColors : ['rgba(0,113,227,0.5)'],
            borderRadius: 8,
            borderSkipped: false
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { stepSize: 1 } }
          }
        }
      });
    }
  }

  // ── Events Table ─────────────────────────────────────────────────────
  allEvents = d.recent_events || [];
  console.log('[FIREWALL][DASHBOARD] Rendering', allEvents.length, 'events');
  renderEventsTable(allEvents);
}

function renderTopThreatUsers(users) {
  const container = document.getElementById('top-threat-list');
  if (!container) return;
  
  if (users.length === 0) {
    container.innerHTML = '<div style="text-align:center; color:var(--muted); padding:16px;">No threat data available</div>';
    return;
  }
  
  container.innerHTML = users.map((u, idx) => {
    const borderColor = idx === 0 ? 'var(--accent2)' : 'var(--border)';
    return `
    <div style="display:flex; align-items:center; gap:12px; padding:12px 16px; background:var(--surface2); border-radius:2px; border-left:3px solid ${borderColor};">
      <div style="font-size:20px; font-weight:800; color:var(--muted); min-width:24px;">#${idx + 1}</div>
      <div style="flex:1;">
        <div style="font-weight:600; font-size:14px;">${escapeHtml(u.username)}</div>
        <div style="font-size:11px; color:var(--muted); font-family:'Space Mono', monospace;">User ID: ${u.id}</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:24px; font-weight:800; color:var(--accent2);">${u.threat_count}</div>
        <div style="font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:1px;">Threats</div>
      </div>
    </div>
  `;
  }).join('');
}

function renderEventsTable(events) {
  const tbody = document.getElementById('events-tbody');
  if (!tbody) return;
  
  if (events.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-secondary); padding:32px;">No events yet</td></tr>`;
  } else {
    tbody.innerHTML = events.map(e => {
      const blockedHtml = e.blocked
        ? '<span style="color:var(--accent-red); font-weight:600; font-size:12px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align:middle;margin-right:2px;"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg> Blocked</span>'
        : '<span style="color:var(--accent-green); font-weight:600; font-size:12px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align:middle;margin-right:2px;"><polyline points="20 6 9 17 4 12"/></svg> Allowed</span>';
      
      const replayBtn = e.blocked
        ? `<a href="/replay.html?id=${e.id}" style="
            display:inline-flex; align-items:center; gap:4px;
            padding:3px 10px; border-radius:6px; font-size:11px; font-weight:600;
            background:rgba(0,255,224,0.10); color:#00ffe0;
            border:1px solid rgba(0,255,224,0.25); text-decoration:none;
            transition:background 0.2s;" 
           onmouseover="this.style.background='rgba(0,255,224,0.20)'"
           onmouseout="this.style.background='rgba(0,255,224,0.10)'">
            ▶ Replay
          </a>`
        : '<span style="font-size:11px;color:var(--text-secondary)">—</span>';

      return `
      <tr>
        <td><span class="module-badge badge-${e.module || 'UNKNOWN'}">${e.module || 'UNKNOWN'}</span></td>
        <td style="font-size:12px; color:var(--text-secondary);">${escapeHtml(e.username || 'User #' + (e.user_id || '?'))}</td>
        <td style="font-size:12px; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
          ${escapeHtml((e.prompt_text || '').substring(0, 55))}${(e.prompt_text || '').length > 55 ? '...' : ''}
        </td>
        <td style="font-size:12px; color:var(--text-secondary);">${formatTime(e.timestamp)}</td>
        <td>${blockedHtml}</td>
        <td>${replayBtn}</td>
      </tr>
    `;
    }).join('');
  }
}

function filterEventsByUsername(searchTerm) {
  if (!searchTerm.trim()) {
    renderEventsTable(allEvents);
    return;
  }
  
  const filtered = allEvents.filter(e => 
    (e.username || '').toLowerCase().includes(searchTerm.toLowerCase())
  );
  renderEventsTable(filtered);
}

function moduleColor(module) {
  const colors = {
    'INJECTION':       'rgba(255,55,95,0.7)',
    'TOKEN_SMUGGLING': 'rgba(255,159,10,0.7)',
    'SHADOW':          'rgba(90,200,250,0.7)',
    'DLP':             'rgba(255,214,10,0.7)',
    'DLP_IN':          'rgba(255,214,10,0.7)',
    'BEHAVIOR':        'rgba(48,209,88,0.7)',
    'ACTION':          'rgba(191,90,242,0.7)',
  };
  return colors[module] || 'rgba(130,130,150,0.5)';
}

function formatTime(ts) {
  if (!ts) return '';
  try {
    const date = new Date(ts.replace(' ', 'T') + 'Z');
    return date.toLocaleString('en', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true
    });
  } catch { return ts; }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(String(text || '')));
  return div.innerHTML;
}

function updateLineChart() {
  const data = showDetailedView ? hourlyData : dailyData;
  const lineLabels = data.map(item => {
    if (showDetailedView) {
      const d = new Date(item.hour);
      return d.toLocaleDateString('en', { month: 'short', day: 'numeric' }) + ' ' + d.getHours() + 'h';
    } else {
      const d = new Date(item.day);
      return d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
    }
  });
  const lineValues = data.map(item => item.cnt);

  if (lineChart) {
    lineChart.data.labels = lineLabels;
    lineChart.data.datasets[0].data = lineValues;
    lineChart.update();
  } else {
    const ctx2 = document.getElementById('line-chart');
    if (ctx2) {
      lineChart = new Chart(ctx2, {
        type: 'line',
        data: {
          labels: lineLabels.length ? lineLabels : ['No data'],
          datasets: [{
            label: 'Threats',
            data: lineValues.length ? lineValues : [0],
            borderColor: '#0071e3',
            backgroundColor: 'rgba(0,113,227,0.08)',
            borderWidth: 2.5,
            pointRadius: 4,
            pointBackgroundColor: '#0071e3',
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 11 }, maxRotation: 45 } },
            y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { stepSize: 1 } }
          }
        }
      });
    }
  }
}

// ── Init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  console.log('[FIREWALL][DASHBOARD] Initializing...');
  const user = initPage('DASHBOARD');
  console.log('[FIREWALL][DASHBOARD] User from initPage:', user);
  if (!user) return;
  
  // Show clear data button for admin only
  if (user.role === 'admin') {
    document.getElementById('clear-data-btn').style.display = 'block';
  }
  
  // Sync topbar user display
  const topName = document.getElementById('user-pill-name-top');
  const topAvatar = document.getElementById('user-avatar-top');
  if (topName) topName.textContent = user.username;
  if (topAvatar) topAvatar.textContent = user.username[0].toUpperCase();
  console.log('[FIREWALL][DASHBOARD] Topbar user synced');
  
  // Setup search bar
  const searchBar = document.getElementById('user-search');
  if (searchBar) {
    searchBar.addEventListener('input', (e) => {
      filterEventsByUsername(e.target.value);
    });
  }
  
  // Setup toggle button
  const toggleBtn = document.getElementById('toggle-chart-view');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      showDetailedView = !showDetailedView;
      toggleBtn.textContent = showDetailedView ? 'Simple' : 'Details';
      updateLineChart();
    });
  }
  
  loadDashboard();
  setInterval(loadDashboard, 10000);
  console.log('[FIREWALL][DASHBOARD] Auto-refresh every 10s active.');
});

async function clearAllData() {
  if (!confirm('WARNING: This will delete ALL threat data, events, and logs. Users will remain. Continue?')) return;
  
  const resp = await fetch('/api/admin/clear-data', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (resp.ok) {
    alert('All data cleared successfully. Dashboard will refresh.');
    location.reload();
  } else {
    alert('Failed to clear data. Check console for errors.');
  }
}