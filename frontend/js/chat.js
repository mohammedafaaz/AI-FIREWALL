// Shell — Enterprise AI Firewall — Chat Interface JS

let sessionId = null;
let isWaiting = false;
let chatHistory = []; // Store all messages
let dlpDebugMode = false; // Admin-only DLP debug mode

function genSessionId() {
  const user = getUser();
  const userId = user ? user.id : 'guest';
  return 'sess_' + userId + '_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(String(text || '')));
  return div.innerHTML;
}

function formatMarkdown(text) {
  let html = escapeHtml(text);
  
  // Code blocks with language
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`;
  });
  
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  
  // Lists
  html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  
  // Line breaks
  html = html.replace(/\n\n/g, '<br><br>');
  html = html.replace(/\n/g, '<br>');
  
  return html;
}

function scrollToBottom() {
  const msgs = document.getElementById('chat-messages');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}

function showTypingIndicator() {
  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.id = 'typing-indicator';
  div.className = 'message-bubble message-ai glass-card';
  div.style.cssText = 'padding:10px 16px; font-size:11px; color:var(--muted); font-family:monospace;';
  div.innerHTML = `<span id="typing-status">Hold on...</span>`;
  msgs.appendChild(div);
  scrollToBottom();
  
  const messages = ['Hold on...', 'Just a moment...', 'Almost there...', 'Nearly done...','Please wait...','Processing...'];
  let idx = 0;
  const interval = setInterval(() => {
    idx = (idx + 1) % messages.length;
    const statusEl = document.getElementById('typing-status');
    if (statusEl) statusEl.textContent = messages[idx];
  }, 1200);
  
  div.dataset.interval = interval;
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) {
    if (el.dataset.interval) clearInterval(parseInt(el.dataset.interval));
    el.remove();
  }
}

function appendMessage(role, text, meta = {}, skipSave = false) {
  const msgs = document.getElementById('chat-messages');
  const wrapper = document.createElement('div');
  wrapper.style.cssText = `display:flex; flex-direction:column; align-items:${role === 'user' ? 'flex-end' : 'flex-start'}; margin-bottom:12px;`;

  const bubble = document.createElement('div');
  bubble.className = `message-bubble message-${role}`;

  // Format AI messages with markdown, user messages with simple formatting
  const formatted = role === 'ai' ? formatMarkdown(text) : escapeHtml(text).replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
  
  bubble.innerHTML = formatted;

  wrapper.appendChild(bubble);

  // Add blocked banner directly below message if blocked
  if (meta.blocked) {
    const banner = document.createElement('div');
    banner.className = 'banner banner-red banner-slide';
    banner.style.cssText = 'margin-top:8px; max-width:72%; align-self:' + (role === 'user' ? 'flex-end' : 'flex-start');
    banner.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
      </svg>
      <strong>Blocked by ${meta.module || 'FIREWALL'}:</strong> ${escapeHtml(meta.reason || 'Security violation')}
    `;
    wrapper.appendChild(banner);
  }

  // Add gaslighting warning banner if present
  if (meta.gaslighting_warn && meta.gaslighting_score) {
    const banner = document.createElement('div');
    banner.className = 'banner banner-amber banner-slide';
    banner.style.cssText = 'margin-top:8px; max-width:72%; align-self:' + (role === 'user' ? 'flex-end' : 'flex-start');
    banner.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <strong>Session Risk: ${Math.round(meta.gaslighting_score * 100)}%</strong> — Conversation pattern flagged by Gaslighting Detector
    `;
    wrapper.appendChild(banner);
  }

  // Add action approval banner if present
  if (meta.action_queued) {
    const banner = document.createElement('div');
    banner.className = 'banner banner-amber banner-slide';
    banner.style.cssText = 'margin-top:8px; max-width:72%; align-self:' + (role === 'ai' ? 'flex-start' : 'flex-end');
    banner.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
      </svg>
      <strong>Approval Required:</strong> Your request has been sent to higher authority for review. Check the Approvals page for status updates.
    `;
    wrapper.appendChild(banner);
  }

  // Add shadow prompt warnings if present
  if (meta.shadows && meta.shadows.length > 0) {
    const banner = document.createElement('div');
    banner.className = 'banner banner-yellow banner-slide';
    banner.style.cssText = 'margin-top:8px; max-width:72%; align-self:' + (role === 'user' ? 'flex-end' : 'flex-start');
    banner.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
      </svg>
      <strong>Shadow Content Detected:</strong> ${meta.shadows.length} hidden element(s) found and removed
    `;
    wrapper.appendChild(banner);
  }

  // Add DNA/behavioral warnings if present
  if (meta.dna_warn) {
    const banner = document.createElement('div');
    banner.className = 'banner banner-amber banner-slide';
    banner.style.cssText = 'margin-top:8px; max-width:72%; align-self:' + (role === 'user' ? 'flex-end' : 'flex-start');
    banner.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <strong>Behavioral Anomaly:</strong> ${escapeHtml(meta.dna_description || 'Unusual pattern detected')}
    `;
    wrapper.appendChild(banner);
  }

  // Add generic warnings array if present
  if (meta.warnings && meta.warnings.length > 0) {
    meta.warnings.forEach(w => {
      const banner = document.createElement('div');
      // Use red banner for behavior issues, amber for others
      const bannerClass = w.type === 'behavior_issue' ? 'banner-red' : 'banner-amber';
      banner.className = `banner ${bannerClass} banner-slide`;
      banner.style.cssText = 'margin-top:8px; max-width:72%; align-self:' + (role === 'user' ? 'flex-end' : 'flex-start');
      
      const icon = w.type === 'behavior_issue' 
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
             <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
           </svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
             <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
             <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
           </svg>`;
      
      banner.innerHTML = `
        ${icon}
        <strong>${escapeHtml(w.type === 'behavior_issue' ? 'AI Response Issue' : w.type || 'Warning')}:</strong> ${escapeHtml(w.description || 'Security alert')}
      `;
      wrapper.appendChild(banner);
    });
  }

  // DLP Debug Info (Admin only)
  if (dlpDebugMode && (meta.dlp_input || meta.dlp_output)) {
    const dlpDebug = document.createElement('div');
    dlpDebug.className = 'glass-card';
    dlpDebug.style.cssText = 'margin-top:8px; padding:12px; font-size:11px; font-family:monospace; max-width:72%; align-self:' + (role === 'user' ? 'flex-end' : 'flex-start') + '; background:rgba(255,165,0,0.1); border:1px solid rgba(255,165,0,0.3);';
    
    let debugHtml = '<strong style="color:var(--accent5);">🔍 DLP Debug (Admin Only)</strong><br><br>';
    
    if (meta.dlp_input) {
      debugHtml += `<strong>Original Input:</strong><br>${escapeHtml(meta.dlp_input.original)}<br><br>`;
      debugHtml += `<strong>Masked Input:</strong><br>${escapeHtml(meta.dlp_input.masked)}<br>`;
    }
    
    if (meta.dlp_output) {
      debugHtml += `<strong>Original Output:</strong><br>${escapeHtml(meta.dlp_output.original)}<br><br>`;
      debugHtml += `<strong>Masked Output:</strong><br>${escapeHtml(meta.dlp_output.masked)}<br>`;
    }
    
    dlpDebug.innerHTML = debugHtml;
    wrapper.appendChild(dlpDebug);
  }

  // Meta info
  if (meta.module && !meta.blocked) {
    const metaDiv = document.createElement('div');
    metaDiv.style.cssText = 'font-size:11px; margin-top:6px; padding:0 4px; color:var(--muted);';
    metaDiv.textContent = `via ${meta.module}`;
    wrapper.appendChild(metaDiv);
  }

  msgs.appendChild(wrapper);
  scrollToBottom();
  
  // Save to history only if not loading from history
  if (!skipSave) {
    chatHistory.push({ role, text, meta, timestamp: Date.now() });
    saveChatHistory();
  }
}

function saveChatHistory() {
  const user = getUser();
  const userId = user ? user.id : 'guest';
  localStorage.setItem(`chat_history_${userId}_${sessionId}`, JSON.stringify(chatHistory));
}

function loadChatHistory() {
  const user = getUser();
  const userId = user ? user.id : 'guest';
  const saved = localStorage.getItem(`chat_history_${userId}_${sessionId}`);
  if (saved) {
    chatHistory = JSON.parse(saved);
    chatHistory.forEach(msg => {
      appendMessage(msg.role, msg.text, msg.meta, true); // skipSave = true
    });
  }
}

function showBlockedBanner(module, reason) {
  const bannerArea = document.getElementById('banner-area');
  bannerArea.innerHTML = ''; // Clear previous banners
  const banner = document.createElement('div');
  banner.className = 'banner banner-red banner-slide';
  banner.id = 'blocked-banner';
  banner.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
    </svg>
    <strong>Blocked by ${module}:</strong> ${escapeHtml(reason)}
    <button onclick="clearBanners()" style="margin-left:auto; background:none; border:none; cursor:pointer; color:inherit; font-size:16px;">&times;</button>
  `;
  bannerArea.appendChild(banner);

  // Shake input
  const inputBox = document.getElementById('chat-input-box');
  if (inputBox) {
    inputBox.classList.add('blocked');
    setTimeout(() => inputBox.classList.remove('blocked'), 500);
  }
}

function showGaslightingBanner(score) {
  clearBanners();
  const bannerArea = document.getElementById('banner-area');
  const banner = document.createElement('div');
  banner.className = 'banner banner-amber banner-slide';
  banner.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
    <strong>Session Risk: ${Math.round(score * 100)}%</strong> — Conversation pattern flagged by Gaslighting Detector
    <button onclick="clearBanners()" style="margin-left:auto; background:none; border:none; cursor:pointer; color:inherit; font-size:16px;">&times;</button>
  `;
  bannerArea.appendChild(banner);
}

function showShadowBanner(shadows) {
  const bannerArea = document.getElementById('banner-area');
  if (document.getElementById('shadow-banner')) return;

  const banner = document.createElement('div');
  banner.id = 'shadow-banner';
  banner.style.marginBottom = '8px';
  ShadowRenderer.renderWarningCard(shadows, bannerArea);
}

function clearBanners() {
  const area = document.getElementById('banner-area');
  if (area) area.innerHTML = '';
}

function clearChat() {
  if (!confirm('Are you sure you want to clear all chat messages? This cannot be undone.')) {
    return;
  }
  
  // Clear messages from DOM
  const msgs = document.getElementById('chat-messages');
  if (msgs) msgs.innerHTML = '';
  
  // Clear chat history
  chatHistory = [];
  const user = getUser();
  const userId = user ? user.id : 'guest';
  localStorage.removeItem(`chat_history_${userId}_${sessionId}`);
  
  // Clear banners
  clearBanners();
  
  // Show welcome message
  if (user) {
    setTimeout(() => {
      appendMessage('ai', `Hello ${user.username}! I'm your enterprise AI assistant, protected by Shell Firewall. How can I help you today?`);
    }, 300);
  }
  
  console.log('[FIREWALL][CHAT] Chat history cleared');
}

async function sendMessage() {
  if (isWaiting) return;
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  const bannerArea = document.getElementById('banner-area');
  bannerArea.innerHTML = ''; // Clear banners
  input.value = '';
  input.style.height = 'auto';
  isWaiting = true;

  // Show user message immediately
  appendMessage('user', text);
  showTypingIndicator();

  console.log(`[FIREWALL][CHAT] Sending message to session ${sessionId}`);

  const resp = await API.sendChat(text, sessionId);
  removeTypingIndicator();
  isWaiting = false;

  console.log('[FIREWALL][CHAT] Response received:', resp);

  if (!resp || !resp.success) {
    appendMessage('ai', 'Connection error. Please try again.');
    return;
  }

  const data = resp.data;
  console.log('[FIREWALL][CHAT] Response data:', data);

  // Handle blocked - add meta to message
  if (data.blocked) {
    // Build blocked message meta with any warnings
    const blockedMeta = { blocked: true, module: data.module, reason: data.reason };
    
    if (data.gaslighting_score && data.gaslighting_score > 0.5) {
      blockedMeta.gaslighting_warn = true;
      blockedMeta.gaslighting_score = data.gaslighting_score;
    }
    
    if (data.warnings && data.warnings.length > 0) {
      blockedMeta.warnings = data.warnings;
    }
    
    // Remove the last message (user message without meta)
    const msgs = document.getElementById('chat-messages');
    if (msgs.lastChild) msgs.removeChild(msgs.lastChild);
    // Re-add with blocked meta
    appendMessage('user', text, blockedMeta);
    console.log(`[FIREWALL][CHAT] Blocked by ${data.module}: ${data.reason}`);
    return;
  }

  // Build user message meta from all warnings/flags
  const userMeta = {};
  
  if (data.dlp_input) {
    userMeta.dlp_input = data.dlp_input;
  }
  
  if (data.shadows && data.shadows.length > 0) {
    userMeta.shadows = data.shadows;
    showShadowBanner(data.shadows);
  }
  
  if (data.gaslighting_score && data.gaslighting_score > 0.5 && data.gaslighting_score <= 0.85) {
    userMeta.gaslighting_warn = true;
    userMeta.gaslighting_score = data.gaslighting_score;
  }
  
  if (data.warnings && data.warnings.length > 0) {
    const otherWarnings = data.warnings.filter(w => w.type !== 'dna_warn');
    if (otherWarnings.length > 0) {
      userMeta.warnings = otherWarnings;
    }
  }
  
  // If we have any meta, remove and re-add user message with meta
  if (Object.keys(userMeta).length > 0) {
    const msgs = document.getElementById('chat-messages');
    if (msgs.lastChild) msgs.removeChild(msgs.lastChild);
    appendMessage('user', text, userMeta);
  }

  // Show AI response
  if (data.response) {
    const aiMeta = { module: 'AI (Firewall Protected)' };
    if (data.dlp_output) {
      aiMeta.dlp_output = data.dlp_output;
    }
    if (data.action_queued) {
      aiMeta.action_queued = true;
    }
    if (data.warnings && data.warnings.some(w => w.type !== 'dna_warn')) {
      aiMeta.warnings = data.warnings.filter(w => w.type !== 'dna_warn');
    }
    appendMessage('ai', data.response, aiMeta);
  }

  console.log(`[FIREWALL][CHAT] Response received. GasScore=${data.gaslighting_score ? data.gaslighting_score.toFixed(2) : 'N/A'}`);
}

// ── Input auto-resize ─────────────────────────────────────────────────────
function initInputResize() {
  const input = document.getElementById('chat-input');
  if (!input) return;
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 160) + 'px';
  });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

// ── Init ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const user = initPage('CHAT');
  if (!user) return;

  const userId = user.id;
  const storedSessionId = localStorage.getItem(`current_session_id_${userId}`);
  
  if (storedSessionId) {
    sessionId = storedSessionId;
  } else {
    sessionId = genSessionId();
    localStorage.setItem(`current_session_id_${userId}`, sessionId);
  }
  
  initInputResize();

  const sendBtn = document.getElementById('send-btn');
  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
  
  const clearBtn = document.getElementById('clear-chat-btn');
  if (clearBtn) clearBtn.addEventListener('click', clearChat);

  // DLP Debug Toggle (Admin only)
  if (user.role === 'admin') {
    const dlpToggle = document.getElementById('dlp-debug-toggle');
    if (dlpToggle) {
      dlpToggle.style.display = 'block';
      dlpToggle.addEventListener('click', () => {
        dlpDebugMode = !dlpDebugMode;
        const label = document.getElementById('dlp-debug-label');
        if (label) label.textContent = dlpDebugMode ? 'Hide Masked Data' : 'Show Masked Data';
        console.log(`[FIREWALL][CHAT] DLP Debug Mode: ${dlpDebugMode}`);
      });
    }
  }

  loadChatHistory();
  
  if (chatHistory.length === 0) {
    setTimeout(() => {
      appendMessage('ai', `Hello ${user.username}! I'm your enterprise AI assistant, protected by Shell Firewall. How can I help you today?`);
    }, 400);
  }

  console.log(`[FIREWALL][CHAT] Session: ${sessionId} for user: ${user.username}`);
});
