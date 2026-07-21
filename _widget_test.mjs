const apiUrl = "/api/chat";
const hidePaths = ["/music","/video-gen","/interactive-showcase"];
(function() {
  'use strict';
  if (window.__cw_loaded) return;
  window.__cw_loaded = true;

  // Resolve API endpoint: window.CHAT_BOT_API > prop > default
  const resolvedApiUrl = window.CHAT_BOT_API || apiUrl || '/api/chat';

  const btn = document.getElementById('cw-btn');
  const panel = document.getElementById('cw-panel');
  const closeBtn = document.getElementById('cw-close');
  const msgs = document.getElementById('cw-msgs');
  const form = document.getElementById('cw-form');
  const input = document.getElementById('cw-input');
  const sendBtn = document.getElementById('cw-send');
  const welcome = document.getElementById('cw-welcome');
  const suggestions = document.getElementById('cw-suggestions');

  if (!btn || !panel) return;

  const STORAGE_KEY = 'cw.history.v1';
  const MAX_HISTORY = 20;
  const SUGGESTIONS = [
    '這個網站是什麼？',
    '介紹一下你的音樂作品',
    '你有做哪些 AI 工具？',
    '幫我查台積電股價',
  ];

  // ── Hide on certain paths + during media playback ─────────────
  function shouldHide() {
    const p = location.pathname;
    if (hidePaths.some(h => p.startsWith(h))) return true;
    // Hide if any <video> or <audio> is playing
    const media = document.querySelectorAll('video, audio');
    for (const m of media) {
      if (!m.paused && m.readyState > 1) return true;
    }
    return false;
  }
  function applyHide() {
    btn.setAttribute('data-hidden', shouldHide() ? '1' : '0');
  }
  applyHide();
  // Re-check every 1.5s (cheap; covers SPA-ish nav + media start/stop)
  setInterval(applyHide, 1500);
  document.addEventListener('play', applyHide, true);
  document.addEventListener('pause', applyHide, true);

  // ── Open/close ────────────────────────────────────────────────
  function open() {
    panel.setAttribute('data-open', '1');
    panel.setAttribute('aria-hidden', 'false');
    if (welcome && suggestions && suggestions.children.length === 0) {
      SUGGESTIONS.forEach(s => {
        const c = document.createElement('span');
        c.className = 'cw-chip';
        c.textContent = s;
        c.addEventListener('click', () => sendUser(s));
        suggestions.appendChild(c);
      });
    }
    setTimeout(() => input.focus(), 50);
  }
  function close() {
    panel.removeAttribute('data-open');
    panel.setAttribute('aria-hidden', 'true');
  }
  btn.addEventListener('click', () => {
    panel.getAttribute('data-open') === '1' ? close() : open();
  });
  closeBtn.addEventListener('click', close);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && panel.getAttribute('data-open') === '1') close();
  });

  // ── History persistence ───────────────────────────────────────
  function loadHistory() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
    catch { return []; }
  }
  function saveHistory(h) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(h.slice(-MAX_HISTORY))); }
    catch {}
  }
  let history = loadHistory();
  // render prior history
  history.forEach(m => renderBubble(m.role, m.content, false));

  // ── Markdown mini-renderer (very small, no deps) ──────────────
  function escapeHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
  function md(s) {
    if (!s) return '';
    // citations [1] [2] → sup pill
    s = s.replace(/\[(\d+)\]/g, (_, n) => `<span class="cw-cite">[${n}]</span>`);
    // code blocks
    s = s.replace(/```([\s\S]*?)```/g, (_, c) => `<pre>${escapeHtml(c.trim())}</pre>`);
    // inline code
    s = s.replace(/`([^`]+)`/g, function(_, c) { return '<code>' + escapeHtml(c) + '</code>'; });
    // links [text](url)
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    // internal links /path
    s = s.replace(/(^|\s)(\/[a-z0-9_\-/]+)/gi, (m, pre, p) => `${pre}<a href="${p}">${p}</a>`);
    // bold
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // line breaks
    s = s.replace(/\n/g, '<br>');
    return s;
  }

  // ── Bubbles ───────────────────────────────────────────────────
  let activeBotBubble = null; // currently streaming
  function renderBubble(role, content, isHtml = false) {
    const div = document.createElement('div');
    div.className = 'cw-msg cw-msg-' + (role === 'user' ? 'user' : role === 'error' ? 'error' : 'bot');
    if (role === 'typing') {
      div.innerHTML = '<span class="cw-typing"></span><span class="cw-typing"></span><span class="cw-typing"></span>';
    } else {
      div.innerHTML = isHtml ? content : md(content);
    }
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  // ── Send / stream ─────────────────────────────────────────────
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener('submit', e => { e.preventDefault(); sendUser(input.value); });

  async function sendUser(text) {
    text = (text || '').trim();
    if (!text) return;
    if (welcome && welcome.parentNode) welcome.parentNode.removeChild(welcome);

    input.value = '';
    input.style.height = 'auto';
    renderBubble('user', text);
    history.push({ role: 'user', content: text });

    // typing indicator
    const typing = renderBubble('typing');
    sendBtn.disabled = true;

    let botText = '';
    let tools = [];
    let ragSources = [];
    try {
      const resp = await fetch(resolvedApiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: history.slice(0, -1) }),
      });
      if (!resp.ok || !resp.body) throw new Error('HTTP ' + resp.status);
      const reader = resp.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        // SSE: events separated by \n\n, lines start with `event: ` and `data: `
        let idx;
        while ((idx = buf.indexOf('\n\n')) !== -1) {
          const chunk = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          const evLine = chunk.split('\n').find(l => l.startsWith('event:'));
          const dataLine = chunk.split('\n').find(l => l.startsWith('data:'));
          if (!dataLine) continue;
          const evt = (evLine || '').replace(/^event:\s*/, '').trim() || 'message';
          const dataStr = dataLine.replace(/^data:\s*/, '');
          let data = {};
          try { data = JSON.parse(dataStr); } catch {}
          if (evt === 'token' && data.content) {
            if (typing.parentNode) typing.parentNode.removeChild(typing);
            if (!activeBotBubble) activeBotBubble = renderBubble('bot', '');
            botText += data.content;
            activeBotBubble.innerHTML = md(botText);
            msgs.scrollTop = msgs.scrollHeight;
          } else if (evt === 'tool_call') {
            tools.push({ name: data.name, args: data.arguments });
          } else if (evt === 'tool_result') {
            const last = tools[tools.length - 1];
            if (last) last.result = data.result;
          } else if (evt === 'rag') {
            (data.chunks || []).forEach(c => ragSources.push(c));
          } else if (evt === 'error') {
            if (typing.parentNode) typing.parentNode.removeChild(typing);
            renderBubble('error', '⚠️ ' + (data.message || 'unknown error'));
          }
        }
      }
    } catch (err) {
      if (typing.parentNode) typing.parentNode.removeChild(typing);
      renderBubble('error', '⚠️ 連線失敗：' + (err && err.message ? err.message : err));
    } finally {
      sendBtn.disabled = false;
      activeBotBubble = null;
    }

    // append tool/rag footnotes to last bot bubble
    if (activeBotBubble === null) {
      // already finalized; we need the *last* bot bubble
      const lastBot = [...msgs.querySelectorAll('.cw-msg-bot')].pop();
      if (lastBot) {
        if (tools.length) {
          const div = document.createElement('div');
          div.className = 'cw-tools';
          div.innerHTML = tools.map(t => `<span class="cw-tool-pill">🔧 ${escapeHtml(t.name)}</span>`).join('');
          lastBot.appendChild(div);
        }
        if (ragSources.length) {
          const div = document.createElement('div');
          div.className = 'cw-rag-sources';
          const uniq = [];
          const seen = new Set();
          ragSources.forEach(s => {
            const key = s.url || s.title;
            if (!seen.has(key)) { seen.add(key); uniq.push(s); }
          });
          div.innerHTML = '📚 引用：' + uniq.slice(0, 5).map(s => {
            const url = s.url || '#';
            const title = s.title || url;
            return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(title)}</a>`;
          }).join(' · ');
          lastBot.appendChild(div);
        }
      }
    }
    if (botText) history.push({ role: 'assistant', content: botText });
    saveHistory(history);
  }
})();