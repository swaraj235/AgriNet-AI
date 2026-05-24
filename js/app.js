// ===== AgriNet AI — Application Logic =====
// Handles auth, API calls, UI interactions, multilingual support

document.addEventListener('DOMContentLoaded', () => {

  // ===== Auth Check =====
  const token = localStorage.getItem('agrinet_token');
  if (!token) { window.location.href = '/login.html'; return; }

  // Verify token with backend
  apiFetch('/api/auth/me').then(data => {
    if (data.user) {
      setupUserProfile(data.user);
    }
  }).catch(() => {
    localStorage.removeItem('agrinet_token');
    localStorage.removeItem('agrinet_user');
    window.location.href = '/login.html';
  });

  // ===== Navigation =====
  let aiModelsInited = false;
  // LEGACY: document.querySelectorAll('.navbtn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      // LEGACY: document.querySelectorAll('.navbtn').forEach(b => b.classList.remove('active'));
      document.getElementById('s-' + tab).classList.add('active');
      btn.classList.add('active');
      setTimeout(animateBars, 200);

      // Initialize AI Models tab on first open
      if (tab === 'aimodels' && !aiModelsInited) {
        aiModelsInited = true;
        checkMLService();
        setTimeout(drawDemandChart, 100);
      }
      // Re-draw chart on theme change
      if (tab === 'aimodels') {
        setTimeout(drawDemandChart, 50);
      }
    });
  });

  // ===== Theme =====
  const themeBtn = // LEGACY: document.getElementById('theme-btn');
  const savedTheme = localStorage.getItem('agrinet-theme') || 'light';
  document.body.setAttribute('data-theme', savedTheme);
  themeBtn.innerHTML = savedTheme === 'dark' ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';

  themeBtn.addEventListener('click', () => {
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const newTheme = isDark ? 'light' : 'dark';
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('agrinet-theme', newTheme);
    themeBtn.innerHTML = isDark ? '<i class="fa-solid fa-moon"></i>' : '<i class="fa-solid fa-sun"></i>';
  });

  // ===== Language =====
  const langSelect = document.getElementById('language-select');
  const savedLang = localStorage.getItem('agrinet-lang') || 'en';
  langSelect.value = savedLang;
  applyTranslation(savedLang);

  langSelect.addEventListener('change', async (e) => {
    const lang = e.target.value;
    localStorage.setItem('agrinet-lang', lang);
    await applyTranslation(lang);
  });

  // ===== Chat Enter Key =====
  const chatInput = document.getElementById('chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && chatInput.value.trim()) sendChat();
    });
  }

  // ===== Close dropdown on outside click =====
  document.addEventListener('click', (e) => {
    const menu = document.getElementById('user-dropdown');
    const btn = document.getElementById('user-avatar-btn');
    if (menu && !menu.contains(e.target) && !btn.contains(e.target)) {
      menu.classList.remove('show');
    }
  });

  // Initial animations
  setTimeout(animateBars, 500);
  animateCounter('counter-farmers', 2847, 1500);
});

// ===== State =====
let selectedFarmers = 0;
let micActive = false;
let translationCache = {};

// ===== API Helper =====
async function apiFetch(url, options = {}) {
  const token = localStorage.getItem('agrinet_token');
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = 'Bearer ' + token;

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('agrinet_token');
    localStorage.removeItem('agrinet_user');
    window.location.href = '/login.html';
    throw new Error('Unauthorized');
  }

  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// ===== User Profile =====
function setupUserProfile(user) {
  const initials = user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  const initialsEl = document.getElementById('user-initials');
  const nameEl = document.getElementById('dropdown-name');
  const emailEl = document.getElementById('dropdown-email');
  if (initialsEl) initialsEl.textContent = initials;
  if (nameEl) nameEl.textContent = user.name;
  if (emailEl) emailEl.textContent = user.email;
}

function toggleUserMenu() {
  document.getElementById('user-dropdown').classList.toggle('show');
}

function logout() {
  localStorage.removeItem('agrinet_token');
  localStorage.removeItem('agrinet_user');
  window.location.href = '/login.html';
}

// ===== Translation =====
async function applyTranslation(lang) {
  try {
    // Try backend first
    let texts;
    try {
      texts = await apiFetch('/api/translations/' + lang);
    } catch {
      // Fallback to local cache / i18nAPI
      if (window.i18nAPI) {
        texts = await window.i18nAPI(lang);
      }
    }

    if (!texts) return;
    translationCache = texts;

    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (texts[key]) el.textContent = texts[key];
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (texts[key]) el.placeholder = texts[key];
    });
  } catch (error) {
    console.error("Translation error:", error);
  }
}

function t(key) {
  return translationCache[key] || key;
}

// ===== Toast =====
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'error' ? 'fa-circle-xmark' : 'fa-circle-check';
  toast.innerHTML = `<i class="fa-solid ${icon} toast-icon"></i><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

// ===== Animations =====
function animateBars() {
  document.querySelectorAll('.section.active .bar-fill[data-width]').forEach(bar => {
    bar.style.width = bar.getAttribute('data-width') + '%';
  });
}

function animateCounter(id, target, duration) {
  const el = document.getElementById(id);
  if (!el) return;
  let start = 0;
  const step = (ts) => {
    if (!start) start = ts;
    const progress = Math.min((ts - start) / duration, 1);
    el.textContent = Math.floor(progress * target).toLocaleString('en-IN');
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ===== Crop AI (calls backend) =====
async function runCropAI() {
  const btn = document.getElementById('run-btn');
  const soil = document.getElementById('soil').value;
  const water = document.getElementById('water').value;
  const land = document.getElementById('land').value;

  if (!soil || !water || !land) {
    ['soil', 'water', 'land'].forEach(id => {
      const el = document.getElementById(id);
      if (!el.value) {
        el.style.borderColor = 'var(--color-down)';
        setTimeout(() => el.style.borderColor = '', 2000);
      }
    });
    showToast(t('validation_error'), 'error');
    return;
  }

  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing…';
  btn.disabled = true;

  try {
    const data = await apiFetch('/api/crop-predict', {
      method: 'POST',
      body: JSON.stringify({ soil, water, land })
    });

    const results = data.results;
    if (results && results.length > 0) {
      const top = results[0];
      document.getElementById('rec-crop').textContent = top.crop;
      document.getElementById('rec-reason').textContent = top.reason;
      document.getElementById('crop-result').style.display = 'block';

      document.getElementById('crop-table-body').innerHTML = results.map((r, i) => `
        <tr class="${i === 0 ? 'highlight' : ''}">
          <td>${escapeHtml(r.crop)}</td>
          <td>${r.score.toFixed(1)} / 10</td>
          <td>${escapeHtml(r.match)}</td>
          <td>${escapeHtml(r.profit || '—')}</td>
          <td>${i === 0 ? '<span class="badge up">Best</span>' : ''}</td>
        </tr>
      `).join('');
      showToast('AI analysis complete!');
    }
  } catch (e) {
    showToast(e.message || 'Analysis failed.', 'error');
  } finally {
    btn.innerHTML = `<i class="fa-solid fa-microchip"></i> <span>${t('run_ai_btn')}</span>`;
    btn.disabled = false;
  }
}

// ===== Transport Pool (calls backend) =====
function selectFarmer(el) {
  el.classList.toggle('selected');
  selectedFarmers = document.querySelectorAll('.farmer-card.selected').length;
  const countEl = document.getElementById('selected-count');
  if (countEl) {
    countEl.textContent = `${selectedFarmers} farmer${selectedFarmers !== 1 ? 's' : ''} selected`;
    countEl.style.color = selectedFarmers > 0 ? 'var(--color-primary)' : '';
  }
}

async function calcPool() {
  if (selectedFarmers === 0) {
    showToast(t('pool_error'), 'error');
    return;
  }

  const btn = document.getElementById('pool-btn');
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Optimizing…';
  btn.disabled = true;

  try {
    const data = await apiFetch('/api/pool-calculate', {
      method: 'POST',
      body: JSON.stringify({ farmer_count: selectedFarmers })
    });

    document.getElementById('pool-bar').style.width = Math.round((data.pooled_cost / data.base_cost) * 100) + '%';
    document.getElementById('pool-val').textContent = '₹' + data.pooled_cost.toLocaleString('en-IN');
    document.getElementById('pool-note').innerHTML = `
      <i class="fa-solid fa-circle-check" style="color:var(--color-primary);"></i>
      <b>${data.total_farmers} farmers pooled</b> · saving <b style="color:var(--color-primary);">₹${data.savings.toLocaleString('en-IN')}</b> each
    `;
    showToast(`₹${data.savings.toLocaleString('en-IN')} saved per farmer!`);
  } catch (e) {
    showToast(e.message || 'Calculation failed.', 'error');
  } finally {
    btn.innerHTML = '<i class="fa-solid fa-truck-ramp-box"></i> <span>' + t('calc_pool_btn') + '</span>';
    btn.disabled = false;
  }
}

// ===== Chat =====
const chatResponses = {
  en: [
    "Based on current Pune mandi rates, sell your tomatoes tomorrow. Price is ₹22-25/kg — best in 2 weeks.",
    "Your soil profile suggests Brinjal for next season. Expected profit: ₹48,000/acre.",
    "3 farmers near you are pooling transport tomorrow. Join to save ₹2,800 on shipping.",
    "Weather alert: Light rain expected in 3 days. Harvest your onions before that.",
    "Cold storage at Nashik junction has space. ₹80/day for up to 2 tons."
  ],
  hi: [
    "पुणे मंडी के मौजूदा भाव के अनुसार, कल अपने टमाटर बेचें। भाव ₹22-25/किलो है।",
    "आपकी मिट्टी के अनुसार अगले सीज़न बैंगन बोएं। अनुमानित लाभ: ₹48,000/एकड़।",
    "आपके पास 3 किसान कल परिवहन पूल कर रहे हैं। जुड़ें और ₹2,800 बचाएं।",
    "मौसम चेतावनी: 3 दिन में हल्की बारिश की संभावना। प्याज़ पहले काट लें।",
    "नासिक जंक्शन पर कोल्ड स्टोरेज में जगह है। ₹80/दिन 2 टन तक।"
  ],
  mr: [
    "पुणे मंडीच्या सध्याच्या दरानुसार, उद्या तुमचे टोमॅटो विका. भाव ₹22-25/किलो.",
    "तुमच्या मातीनुसार पुढच्या हंगामात वांगी लावा. अंदाजित नफा: ₹48,000/एकर.",
    "तुमच्या जवळ 3 शेतकरी उद्या वाहतूक पूल करत आहेत. सामील व्हा आणि ₹2,800 वाचवा.",
    "हवामान इशारा: 3 दिवसांत हलका पाऊस अपेक्षित. आधी कांदे काढा.",
    "नासिक जंक्शनवर कोल्ड स्टोरेजमध्ये जागा आहे. ₹80/दिवस 2 टनापर्यंत."
  ]
};

function sendChat() {
  const input = document.getElementById('chat-input');
  const container = document.getElementById('chat-container');
  const text = input.value.trim();
  if (!text) return;

  const userMsg = document.createElement('div');
  userMsg.className = 'chat-msg user';
  userMsg.innerHTML = `<div class="avatar farmer">U</div><div class="bubble">${escapeHtml(text)}</div>`;
  container.appendChild(userMsg);
  input.value = '';
  container.scrollTop = container.scrollHeight;

  const typing = document.createElement('div');
  typing.className = 'chat-msg bot';
  typing.id = 'typing-indicator';
  typing.innerHTML = `<div class="avatar ai"><i class="fa-solid fa-robot"></i></div><div class="bubble" style="opacity:0.6;"><i class="fa-solid fa-ellipsis fa-beat-fade"></i></div>`;
  container.appendChild(typing);
  container.scrollTop = container.scrollHeight;

  setTimeout(() => {
    const t = document.getElementById('typing-indicator');
    if (t) t.remove();
    const lang = document.getElementById('language-select').value;
    const responses = chatResponses[lang] || chatResponses.en;
    const response = responses[Math.floor(Math.random() * responses.length)];
    const botMsg = document.createElement('div');
    botMsg.className = 'chat-msg bot';
    botMsg.innerHTML = `<div class="avatar ai"><i class="fa-solid fa-robot"></i></div><div class="bubble">${response}</div>`;
    container.appendChild(botMsg);
    container.scrollTop = container.scrollHeight;
  }, 1200 + Math.random() * 800);
}

function toggleMic() {
  const btn = document.getElementById('mic-btn');
  micActive = !micActive;
  btn.classList.toggle('recording', micActive);
  if (micActive) {
    showToast('🎤 Listening…');
    setTimeout(() => {
      const lang = document.getElementById('language-select').value;
      const phrases = { en: "What crop should I plant?", hi: "कौन सी फसल बोऊं?", mr: "कोणते पीक लावू?" };
      document.getElementById('chat-input').value = phrases[lang] || phrases.en;
      micActive = false;
      btn.classList.remove('recording');
    }, 2500);
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ===== ML SERVICE — Status Check =====
async function checkMLService() {
  const dot  = document.getElementById('ml-status-dot');
  const text = document.getElementById('ml-status-text');
  if (!dot) return;
  try {
    const res = await fetch('/api/ml/health');
    if (res.ok) {
      dot.className  = 'ml-dot online';
      text.textContent = 'ML service online — FastAPI · sklearn models loaded';
    } else throw new Error();
  } catch {
    dot.className  = 'ml-dot offline';
    text.textContent = 'ML service offline — using fallback demo data';
  }
}

// ===== ML CROP RECOMMEND =====
const ML_FALLBACK_DATA = {
  black: { medium: [{crop:'Tomato',score:9.2,match:'Excellent',profit:'₹61,000',reason:'High demand in Pune · ideal for black cotton soil',confidence:92,feature_importance:{soil:0.42,water:0.28,land_size:0.18,season:0.12}},{crop:'Soybean',score:7.8,match:'Good',profit:'₹45,000',reason:'Suitable for black soil with moderate yield',confidence:68,feature_importance:{soil:0.42,water:0.28,land_size:0.18,season:0.12}},{crop:'Onion',score:6.5,match:'Good',profit:'₹41,000',reason:'Stable mandi prices, moderate competition',confidence:54,feature_importance:{soil:0.42,water:0.28,land_size:0.18,season:0.12}}]},
  red:   { high:   [{crop:'Brinjal',score:8.8,match:'Excellent',profit:'₹48,000',reason:'Thrives in red laterite · export demand rising',confidence:88,feature_importance:{soil:0.48,water:0.22,land_size:0.16,season:0.14}},{crop:'Potato',score:7.1,match:'Good',profit:'₹52,000',reason:'Good yield with high water availability',confidence:65,feature_importance:{soil:0.48,water:0.22,land_size:0.16,season:0.14}}]},
  alluvial:{ high: [{crop:'Potato',score:9.1,match:'Excellent',profit:'₹52,000',reason:'Best yield in alluvial soil · cold storage nearby',confidence:91,feature_importance:{soil:0.38,water:0.32,land_size:0.20,season:0.10}},{crop:'Wheat',score:7.8,match:'Good',profit:'₹35,000',reason:'Consistent local demand, reliable crop',confidence:73,feature_importance:{soil:0.38,water:0.32,land_size:0.20,season:0.10}}]},
};

async function runMLCrop() {
  const soil  = document.getElementById('ml-soil').value;
  const water = document.getElementById('ml-water').value;
  const land  = document.getElementById('ml-land').value;
  if (!soil || !water || !land) { showToast('Please select all fields.', 'error'); return; }

  const btn = document.getElementById('ml-run-btn');
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Random Forest…';
  btn.disabled = true;

  try {
    let results, fi;
    try {
      const data = await apiFetch('/api/ml/crop-recommend', {
        method:'POST', body: JSON.stringify({soil, water, land, season:'kharif', region:'Nashik'})
      });
      results = data.results;
      if (data.supply_balance_note) showToast('🤖 ' + data.supply_balance_note.slice(0,80) + '…');
    } catch {
      const fb = ML_FALLBACK_DATA[soil] || ML_FALLBACK_DATA['black'];
      results = fb[water] || fb[Object.keys(fb)[0]];
    }

    // Render results table
    const resEl = document.getElementById('ml-crop-results');
    resEl.style.display = 'block';
    resEl.innerHTML = `<table class="crop-table">
      <thead><tr><th>Crop</th><th>Score</th><th>Fit</th><th>Est. Profit/ac</th><th>Confidence</th></tr></thead>
      <tbody>${results.map((r,i) => `
        <tr class="${i===0?'highlight':''}">
          <td><b>${escapeHtml(r.crop)}</b></td>
          <td>${(r.score||0).toFixed(1)}/10</td>
          <td>${escapeHtml(r.match||'—')}</td>
          <td>${escapeHtml(r.profit||'—')}</td>
          <td>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="flex:1;height:6px;background:var(--color-border);border-radius:3px;overflow:hidden;">
                <div style="width:${r.confidence||0}%;height:100%;background:var(--color-primary);border-radius:3px;transition:width 0.8s;"></div>
              </div>
              <span style="font-size:12px;font-weight:700;color:var(--color-primary);width:36px;">${(r.confidence||0).toFixed(0)}%</span>
            </div>
          </td>
        </tr>`).join('')}
      </tbody></table>`;

    // Feature importance bars
    if (results[0]?.feature_importance) {
      fi = results[0].feature_importance;
      const fiEl = document.getElementById('ml-fi-bars');
      const fiBox = document.getElementById('ml-feature-box');
      const features = [
        {key:'soil', label:'Soil Type'},
        {key:'water', label:'Water Availability'},
        {key:'land_size', label:'Land Size'},
        {key:'season', label:'Season'},
      ];
      fiEl.innerHTML = features.map(f => {
        const pct = Math.round((fi[f.key]||0)*100);
        return `<div class="bar-row">
          <div class="bar-label" style="width:130px;">${f.label}</div>
          <div class="bar-track"><div class="bar-fill" style="width:0%;background:var(--color-primary);" data-width="${pct}"></div></div>
          <div class="bar-val" style="color:var(--color-primary);">${pct}%</div>
        </div>`;
      }).join('');
      fiBox.style.display = 'block';
      setTimeout(() => {
        fiEl.querySelectorAll('.bar-fill[data-width]').forEach(b => b.style.width = b.dataset.width + '%');
      }, 150);
    }
    showToast('Random Forest model complete!');
  } catch(e) {
    showToast(e.message||'ML analysis failed.', 'error');
  } finally {
    btn.innerHTML = '<i class="fa-solid fa-flask"></i> Run ML Model';
    btn.disabled = false;
  }
}

// ===== SUPPLY BALANCER =====
async function runSupplyBalancer() {
  const btn = document.getElementById('sb-btn');
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Balancing…';
  btn.disabled = true;

  const FALLBACK_SB = [
    {village:'Nashik A',     assigned_crop:'Tomato',   reason:'Best fit for black soil. First village assigned — no market saturation risk.',  overproduction_risk:0.0,  expected_profit:'₹61,000', market_distance_km:8.2},
    {village:'Nashik B',     assigned_crop:'Brinjal',  reason:'Best fit for red soil with medium water. Low supply saturation.',               overproduction_risk:0.05, expected_profit:'₹48,000', market_distance_km:12.4},
    {village:'Ahmednagar',   assigned_crop:'Potato',   reason:'Best fit for alluvial soil. No market saturation risk.',                       overproduction_risk:0.0,  expected_profit:'₹52,000', market_distance_km:5.6},
    {village:'Solapur',      assigned_crop:'Millet (Bajra)', reason:'Best fit for black soil with low water. Drought resistant crop.',         overproduction_risk:0.0,  expected_profit:'₹38,000', market_distance_km:9.1},
    {village:'Satara',       assigned_crop:'Brinjal',  reason:'Red soil with high water suits brinjal. Demand strong enough.',                overproduction_risk:0.15, expected_profit:'₹48,000', market_distance_km:14.3},
    {village:'Pune Rural',   assigned_crop:'Soybean',  reason:'Alluvial soil. Demand underserved. Low saturation risk.',                     overproduction_risk:0.0,  expected_profit:'₹45,000', market_distance_km:4.2},
    {village:'Kolhapur',     assigned_crop:'Sugarcane', reason:'Clay soil ideal for sugarcane. Sugar mills nearby.',                          overproduction_risk:0.05, expected_profit:'₹70,000', market_distance_km:7.8},
    {village:'Aurangabad',   assigned_crop:'Onion',    reason:'Sandy soil. No saturation. Onion demand moderate.',                           overproduction_risk:0.0,  expected_profit:'₹41,000', market_distance_km:18.5},
  ];

  try {
    let data;
    try {
      data = await apiFetch('/api/ml/supply-balance', {method:'POST', body:JSON.stringify({region:'Maharashtra'})});
    } catch {
      data = {assignments: FALLBACK_SB, balance_score: 84.7, model: 'AI Supply Balancer (demo)'};
    }

    const RISK_CLASS = r => r <= 0.1 ? 'up' : r <= 0.25 ? 'warn' : 'down';
    const RISK_LABEL = r => r <= 0.1 ? 'Low' : r <= 0.25 ? 'Medium' : 'High';

    document.getElementById('sb-results').innerHTML = `
      <table class="crop-table">
        <thead><tr><th>Village</th><th>AI Recommendation</th><th>Expected Profit</th><th>Mkt Distance</th><th>Overproduction Risk</th></tr></thead>
        <tbody>${data.assignments.map(a => `
          <tr>
            <td><b>${escapeHtml(a.village)}</b></td>
            <td><span class="badge up">${escapeHtml(a.assigned_crop)}</span></td>
            <td style="color:var(--color-primary);font-weight:600;">${escapeHtml(a.expected_profit)}</td>
            <td>${a.market_distance_km} km</td>
            <td><span class="badge ${RISK_CLASS(a.overproduction_risk)}">${RISK_LABEL(a.overproduction_risk)}</span></td>
          </tr>`).join('')}
        </tbody>
      </table>`;

    const scoreEl = document.getElementById('sb-score-box');
    const scoreText = document.getElementById('sb-score-text');
    const score = data.balance_score||84.7;
    scoreText.innerHTML = `<b>Supply Balance Score: ${score}/100</b> — ${score>=80?'Excellent':'Good'} regional crop distribution. ${data.model||'AI Supply Balancer'}`;
    scoreEl.style.display = 'flex';
    scoreEl.style.gap = '8px';
    showToast(`Supply balanced! Score: ${score}/100`);
  } catch(e) {
    showToast(e.message||'Balancer failed.', 'error');
  } finally {
    btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Run Balancer';
    btn.disabled = false;
  }
}

// ===== MANDI PRICES =====
const MANDI_FALLBACK = [
  {crop:'Tomato',  price_per_kg:22, trend:'up',     week_change:12.0},
  {crop:'Onion',   price_per_kg:18, trend:'up',     week_change:4.5},
  {crop:'Potato',  price_per_kg:14, trend:'stable', week_change:0.8},
  {crop:'Wheat',   price_per_kg:22, trend:'stable', week_change:-0.5},
  {crop:'Brinjal', price_per_kg:16, trend:'up',     week_change:8.2},
  {crop:'Soybean', price_per_kg:42, trend:'up',     week_change:3.1},
];
const CROP_EMOJI = {Tomato:'🍅',Onion:'🧅',Potato:'🥔',Wheat:'🌾',Brinjal:'🍆',Soybean:'🌱','Millet (Bajra)':'🌾',Sugarcane:'🎋'};

async function loadMandiPrices() {
  const grid = document.getElementById('mandi-grid');
  grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading…</div>';
  try {
    let data;
    try {
      data = await fetch('/api/ml/mandi-prices?market=Pune APMC').then(r=>r.json());
    } catch {
      data = {prices: MANDI_FALLBACK, weather:{temperature_c:28.4,humidity_pct:61,condition:'Partly cloudy',forecast_3d:'Light rain expected in 3 days'}, market:'Pune APMC (demo)', updated_at: new Date().toLocaleString()};
    }
    const TREND_ICON = t => t==='up'?'↑':t==='down'?'↓':'→';
    const TREND_COL  = t => t==='up'?'var(--color-up)':t==='down'?'var(--color-down)':'var(--color-text-sec)';
    grid.innerHTML = data.prices.map(p => `
      <div class="card kpi-card" style="padding:16px;">
        <div style="font-size:24px;margin-bottom:6px;">${CROP_EMOJI[p.crop]||'🌿'}</div>
        <h3>${escapeHtml(p.crop)}</h3>
        <div class="metric" style="font-size:22px;">₹${p.price_per_kg}/kg</div>
        <span class="badge ${p.trend==='up'?'up':p.trend==='down'?'down':'info'}" style="margin-top:6px;">
          ${TREND_ICON(p.trend)} ${p.week_change>0?'+':''}${p.week_change}% week
        </span>
      </div>`).join('');
    if (data.weather) {
      const w = data.weather;
      const wEl = document.getElementById('mandi-weather');
      const wText = document.getElementById('mandi-weather-text');
      wText.textContent = `${w.condition} · ${w.temperature_c}°C · Humidity ${w.humidity_pct}% · ${w.forecast_3d} · Updated: ${data.updated_at}`;
      wEl.style.display = 'flex'; wEl.style.gap='8px';
    }
    showToast('Mandi prices refreshed!');
  } catch(e) { showToast('Failed to load prices.','error'); }
}

// ===== DEMAND CHART (Canvas) =====
const CHART_COLORS = ['#1A8D68','#E8A838','#6E7B8B','#2563EB','#C14646','#7C3AED'];
const CHART_LABELS = ['Tomato','Onion','Potato','Wheat','Brinjal','Soybean'];
const CHART_DATA   = [
  [18,19,20,22,21,23,24,25,23,24,26,27,25,26,28,29,27,28,30,31,30,29,31,32,30,31,33,34,32,33],
  [22,23,22,24,23,25,24,23,24,25,24,23,25,26,25,24,26,27,26,25,27,28,27,26,28,29,28,27,29,30],
  [13,13,14,14,13,14,14,13,14,15,14,14,15,15,14,14,15,16,15,15,16,16,15,15,16,17,16,16,17,17],
  [22,22,22,22,22,22,23,23,22,22,22,23,23,23,22,22,23,23,22,22,22,23,23,23,22,22,23,23,22,22],
  [15,16,16,15,16,17,16,16,17,18,17,17,18,18,17,17,18,19,18,18,19,19,18,18,19,20,19,19,20,20],
  [41,41,42,42,41,42,43,42,43,43,42,43,44,43,43,44,44,43,44,45,44,44,45,45,44,45,46,45,45,46],
];

function drawDemandChart() {
  const canvas = document.getElementById('demand-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const PAD = {top:14, right:16, bottom:28, left:40};
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top - PAD.bottom;
  const allVals = CHART_DATA.flat();
  const minV = Math.min(...allVals) - 2;
  const maxV = Math.max(...allVals) + 2;
  const days = CHART_DATA[0].length;

  ctx.clearRect(0,0,W,H);

  // Dark background
  const isDark = document.body.getAttribute('data-theme') === 'dark';
  const bgCol  = isDark ? '#181D27' : '#F5F7F6';
  const gridCol= isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
  const textCol= isDark ? '#8B95A5' : '#5F6B7A';
  ctx.fillStyle = bgCol;
  ctx.fillRect(0,0,W,H);

  // Grid lines
  ctx.strokeStyle = gridCol; ctx.lineWidth = 1;
  [0,0.25,0.5,0.75,1].forEach(t => {
    const y = PAD.top + cH * t;
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left+cW, y); ctx.stroke();
    const val = Math.round(maxV - t*(maxV-minV));
    ctx.fillStyle = textCol; ctx.font='10px Inter,sans-serif'; ctx.textAlign='right';
    ctx.fillText('₹'+val, PAD.left-4, y+4);
  });

  // Day labels
  ['1','7','14','21','30'].forEach((d,i) => {
    const x = PAD.left + (([0,6,13,20,29][i])/( days-1))*cW;
    ctx.fillStyle = textCol; ctx.font='10px Inter,sans-serif'; ctx.textAlign='center';
    ctx.fillText('D'+d, x, H-8);
  });

  // Lines
  CHART_DATA.forEach((series, si) => {
    ctx.beginPath();
    ctx.strokeStyle = CHART_COLORS[si];
    ctx.lineWidth = si===0 ? 2.5 : 1.5;
    ctx.lineJoin = 'round';
    series.forEach((v,i) => {
      const x = PAD.left + (i/(days-1))*cW;
      const y = PAD.top + (1-(v-minV)/(maxV-minV))*cH;
      i===0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
    });
    ctx.stroke();
  });

  // Legend
  const legend = document.getElementById('forecast-legend');
  if (legend) {
    legend.innerHTML = CHART_LABELS.map((l,i) => `
      <div class="forecast-legend-item">
        <div class="legend-dot" style="background:${CHART_COLORS[i]};"></div>
        <span>${l}</span>
      </div>`).join('');
  }
}
