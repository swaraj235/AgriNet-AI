/**
 * AgriNet AI v2.0 — LLM Chatbot Module
 * Handles: send/receive, voice input, context building, multilingual
 */

let chatHistory = [];
let isRecording = false;
let mediaRecognition = null;

// ── Send message ──────────────────────────────────────────────────────────────
async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input?.value?.trim();
  if (!msg) return;

  input.value = '';
  appendMessage('user', msg);
  chatHistory.push({ role: 'user', content: msg });

  // Show typing indicator
  const typingId = showTyping();

  try {
    const data = await apiFetch('/api/chat/send', {
      method: 'POST',
      body: JSON.stringify({
        message: msg,
        history: chatHistory.slice(-6),
        language: state.lang || 'auto',
        context: buildChatContext(),
      })
    });

    removeTyping(typingId);

    if (data?.reply) {
      appendMessage('ai', data.reply, data.engine);
      chatHistory.push({ role: 'assistant', content: data.reply });
      if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
    } else {
      appendMessage('ai', 'Sorry, I could not get a response. Please try again.', 'error');
    }
  } catch (e) {
    removeTyping(typingId);
    appendMessage('ai', '⚠️ Connection error. Check if the server is running.', 'error');
  }
}

function fillChat(text) {
  const input = document.getElementById('chat-input');
  if (input) { input.value = text; input.focus(); }
}

function clearChat() {
  const msgs = document.getElementById('chat-msgs');
  if (msgs) msgs.innerHTML = `
    <div class="chat-msg">
      <div class="chat-avatar ai"><i class="fa-solid fa-robot"></i></div>
      <div class="chat-bubble ai-bubble">
        👋 Hi again! What would you like to know about farming today?
      </div>
    </div>`;
  chatHistory = [];
}

// ── Build context object to send to LLM ──────────────────────────────────────
function buildChatContext() {
  const ctx = {};
  if (typeof state === 'undefined') return ctx;
  if (state.location) ctx.location = state.location;
  if (state.weather)  ctx.weather  = state.weather;
  if (state.mandiPrices?.length) {
    ctx.mandi_prices = state.mandiPrices.slice(0, 6).map(p => ({
      crop: p.crop,
      price_per_kg: p.price_per_kg,
      trend: p.trend,
    }));
  }
  return ctx;
}

// ── Append message to chat ────────────────────────────────────────────────────
function appendMessage(role, text, engine) {
  const msgs = document.getElementById('chat-msgs');
  if (!msgs) return;

  const user = typeof USER === 'function' ? USER() : {};
  const avatarContent = role === 'user'
    ? `<span>${(user.name || 'U')[0].toUpperCase()}</span>`
    : `<i class="fa-solid fa-robot"></i>`;

  const el = document.createElement('div');
  el.className = `chat-msg ${role === 'user' ? 'user' : ''}`;
  el.innerHTML = `
    <div class="chat-avatar ${role === 'user' ? 'user-av' : 'ai'}">${avatarContent}</div>
    <div>
      <div class="chat-bubble ${role === 'user' ? 'user-bubble' : 'ai-bubble'}">${escapeHtml(text)}</div>
      ${engine && role === 'ai' ? `<div style="font-size:10px;color:var(--text-muted);padding:2px 6px;">${engine === 'llm' ? '🤖 AI' : '💡 Rules'}</div>` : ''}
    </div>`;

  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>');
}

// ── Typing indicator ──────────────────────────────────────────────────────────
function showTyping() {
  const msgs = document.getElementById('chat-msgs');
  const id = 'typing-' + Date.now();
  const el = document.createElement('div');
  el.className = 'chat-msg';
  el.id = id;
  el.innerHTML = `
    <div class="chat-avatar ai"><i class="fa-solid fa-robot"></i></div>
    <div class="chat-bubble ai-bubble">
      <div class="typing-dots">
        <span></span><span></span><span></span>
      </div>
    </div>`;
  msgs.appendChild(el);
  msgs.scrollTop = msgs.scrollHeight;
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

// ── Voice Input (Web Speech API) ──────────────────────────────────────────────
function toggleMic() {
  const btn = document.getElementById('mic-btn');
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    showToast('Voice input not supported in this browser', 'warning');
    return;
  }
  if (isRecording) {
    stopMic();
  } else {
    startMic();
  }
}

function startMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  mediaRecognition = new SR();
  mediaRecognition.lang = getLangCode();
  mediaRecognition.continuous = false;
  mediaRecognition.interimResults = true;

  mediaRecognition.onresult = e => {
    const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
    const input = document.getElementById('chat-input');
    if (input) input.value = transcript;
    if (e.results[e.results.length - 1].isFinal) {
      stopMic();
      sendChat();
    }
  };

  mediaRecognition.onerror = () => { stopMic(); };
  mediaRecognition.onend   = () => { if (isRecording) stopMic(); };

  mediaRecognition.start();
  isRecording = true;
  const btn = document.getElementById('mic-btn');
  if (btn) btn.classList.add('recording');
  document.getElementById('chat-status-text').textContent = '🎙️ Listening… speak now';
}

function stopMic() {
  if (mediaRecognition) { try { mediaRecognition.stop(); } catch {} }
  isRecording = false;
  const btn = document.getElementById('mic-btn');
  if (btn) btn.classList.remove('recording');
  document.getElementById('chat-status-text').textContent = 'Online · Context-aware';
}

function getLangCode() {
  const map = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' };
  return map[state.lang] || 'en-IN';
}

// ── Chat status dot ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const dot = document.getElementById('chat-status-dot');
  if (dot) { dot.className = 'status-dot online'; }
});
