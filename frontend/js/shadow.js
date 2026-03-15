// Shell — Enterprise AI Firewall — Shadow Prompt Visual Renderer

const ShadowRenderer = {
  renderWarningCard(shadowsFound, container) {
    if (!shadowsFound || shadowsFound.length === 0) return;

    const card = document.createElement('div');
    card.className = 'banner banner-yellow banner-slide';
    card.style.cssText = 'margin-bottom: 12px; flex-direction: column; align-items: flex-start; gap: 8px;';

    const header = document.createElement('div');
    header.style.cssText = 'display:flex; align-items:center; gap:8px; font-weight:700;';
    header.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      Hidden Content Detected (${shadowsFound.length} item${shadowsFound.length > 1 ? 's' : ''})
    `;
    card.appendChild(header);

    const subtext = document.createElement('div');
    subtext.style.cssText = 'font-size:12px; opacity:0.8;';
    subtext.textContent = 'Hidden content was removed before sending to AI';
    card.appendChild(subtext);

    const details = document.createElement('div');
    details.style.cssText = 'width:100%; display:flex; flex-direction:column; gap:4px;';

    shadowsFound.forEach(shadow => {
      const item = document.createElement('div');
      item.style.cssText = `
        background: rgba(255,55,95,0.08);
        border: 1px solid rgba(255,55,95,0.2);
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
        font-family: monospace;
      `;
      item.innerHTML = `
        <span style="font-weight:600; color:#c0001f;">[${shadow.type.toUpperCase()}]</span>
        ${escapeHtml(shadow.description)}
        ${shadow.content ? `<br><span style="opacity:0.7; font-size:11px;">Content: <mark style="background:rgba(255,59,48,0.2); border-radius:3px; padding:1px 4px;">${escapeHtml(String(shadow.content).substring(0, 100))}</mark></span>` : ''}
      `;
      details.appendChild(item);
    });

    card.appendChild(details);
    if (container) container.prepend(card);
    return card;
  },

  highlightText(text, positions) {
    if (!positions || positions.length === 0) return escapeHtml(text);
    let result = escapeHtml(text);
    // Simple highlight: wrap content at positions
    return result;
  },

  renderInlineHighlight(originalText, shadowsFound) {
    let html = escapeHtml(originalText);
    if (shadowsFound && shadowsFound.length > 0) {
      // Wrap detected zones with highlight
      shadowsFound.forEach(shadow => {
        if (shadow.position !== undefined) {
          // Highlight area around position
        }
      });
    }
    return html;
  }
};

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(String(text)));
  return div.innerHTML;
}
