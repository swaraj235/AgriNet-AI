/**
 * AgriNet AI v2.0 — Core Application Logic
 * Handles: navigation, auth, location, weather, crop AI, market, transport, supply
 */

// ── Config ───────────────────────────────────────────────────────────────────
const API = '';  // Same origin
const TOKEN = () => localStorage.getItem('agrinet_token');
const USER  = () => { try { return JSON.parse(localStorage.getItem('agrinet_user') || '{}'); } catch { return {}; } };

// ── Global State ──────────────────────────────────────────────────────────────
let state = {
  lat: null, lon: null,
  location: null,
  weather: null,
  mandiPrices: [],
  lang: localStorage.getItem('agrinet-lang') || 'en',
  selectedFarmers: new Set(),
  chatHistory: [],
  priceChart: null,
};

// ── Startup ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (!TOKEN()) { window.location.href = '/login'; return; }

  // Set user info
  const user = USER();
  if (user.name) {
    document.getElementById('sidebar-name').textContent = user.name;
    document.getElementById('sidebar-email').textContent = user.email || 'AgriNet Farmer';
    document.getElementById('sidebar-avatar').textContent = user.name[0].toUpperCase();
    document.getElementById('page-subtitle').textContent = `Welcome back, ${user.name.split(' ')[0]} 👋`;
    state.lang = user.language || state.lang;
  }

  // Apply language
  applyLanguage(state.lang);
  document.getElementById('language-select').value = state.lang;

  // Load theme
  const savedTheme = localStorage.getItem('agrinet-theme') || 'light';
  setTheme(savedTheme);

  // Start location detection
  detectLocation();

  // Pre-load market prices
  loadMarket();

  // Animate dashboard bars
  setTimeout(animateBars, 500);

  // Check API
  checkApiHealth();

  // Generate farmer cards
  generateFarmerCards();
});

// ── API Health ────────────────────────────────────────────────────────────────
async function checkApiHealth() {
  try {
    const r = await fetch('/health');
    const d = await r.json();
    const dot = document.getElementById('api-status-dot');
    const txt = document.getElementById('api-status-text');
    if (r.ok && d.status === 'ok') {
      dot.style.animation = 'glow 2s infinite';
      dot.style.background = 'var(--clr-primary)';
      txt.textContent = `Connected${d.llm ? ' · AI Active' : ''}`;
    }
  } catch {
    document.getElementById('api-status-dot').style.background = 'var(--clr-danger)';
    document.getElementById('api-status-text').textContent = 'Offline';
  }
}

// ── Navigation ────────────────────────────────────────────────────────────────
const PAGE_TITLES = {
  dashboard: ['Dashboard', 'Your farm intelligence hub'],
  crop:      ['Crop AI', 'XGBoost-powered crop recommendations'],
  market:    ['Market Prices', 'Live mandi data'],
  weather:   ['Weather AI', 'Real-time weather & agri advice'],
  transport: ['Transport Pool', 'Share transport costs with neighbors'],
  spoilage:  ['Spoilage AI', 'Protect your produce en route'],
  supply:    ['Supply Balancer', 'AI-optimized crop distribution'],
  blockchain:['Blockchain Trace', 'Immutable supply chain records'],
  chat:      ['AI Advisor', 'Ask anything in your language'],
};

function navTo(tab, el) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const section = document.getElementById('s-' + tab);
  if (section) section.classList.add('active');
  if (el) el.classList.add('active');

  const [title, sub] = PAGE_TITLES[tab] || ['AgriNet', ''];
  document.getElementById('page-title').textContent = title;
  document.getElementById('page-subtitle').textContent = sub;

  // Close sidebar on mobile
  if (window.innerWidth <= 768) closeSidebar();

  // Lazy loads
  if (tab === 'market' && state.mandiPrices.length === 0) loadMarket();
  if (tab === 'weather') loadWeather(false);
  if (tab === 'supply') {
    // Pre-populate map with supply data
    setTimeout(() => initSupplyMap(), 200);
  }
}

// ── Sidebar (mobile) ──────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebar-overlay').classList.toggle('open');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-overlay').classList.remove('open');
}

// ── Theme ─────────────────────────────────────────────────────────────────────
function toggleTheme() {
  const current = document.body.getAttribute('data-theme');
  setTheme(current === 'dark' ? 'light' : 'dark');
}
function setTheme(theme) {
  document.body.setAttribute('data-theme', theme);
  localStorage.setItem('agrinet-theme', theme);
  const icon = document.getElementById('theme-icon');
  if (icon) icon.className = theme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
}

// ── User Menu ─────────────────────────────────────────────────────────────────
function toggleUserMenu() {
  document.getElementById('user-dropdown').classList.toggle('open');
}
document.addEventListener('click', e => {
  if (!e.target.closest('#user-profile-mini')) {
    document.getElementById('user-dropdown')?.classList.remove('open');
  }
});
function logout() {
  localStorage.clear();
  window.location.href = '/login';
}

// ── Language ───────────────────────────────────────────────────────────────────
function onLangChange(lang) {
  state.lang = lang;
  localStorage.setItem('agrinet-lang', lang);
  applyLanguage(lang);
  // Update chat context
  updateChatContext();
}

async function applyLanguage(lang) {
  try {
    const r = await fetch(`/api/translate/strings/${lang}`);
    if (!r.ok) return;
    const strings = await r.json();
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (strings[key]) el.textContent = strings[key];
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (strings[key]) el.placeholder = strings[key];
    });
  } catch {}
}

// ── Location Detection ────────────────────────────────────────────────────────
function detectLocation() {
  if (!navigator.geolocation) {
    setFallbackLocation();
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      state.lat = pos.coords.latitude;
      state.lon = pos.coords.longitude;
      reverseGeocode(state.lat, state.lon);
      loadWeather(false);
    },
    err => {
      console.warn('Geolocation denied:', err.message);
      // Fallback to Nashik, Maharashtra
      state.lat = 19.9975;
      state.lon = 73.7898;
      setFallbackLocation();
      loadWeather(false);
    },
    { timeout: 8000, maximumAge: 300000 }
  );
}

function setFallbackLocation() {
  const locEl = document.getElementById('loc-name');
  if (locEl) locEl.textContent = 'Nashik, Maharashtra';
  state.location = { village: 'Nashik region', district: 'Nashik', state: 'Maharashtra', formatted: 'Nashik, Maharashtra' };
  updateChatContext();
}

function refreshLocation() {
  document.getElementById('loc-name').textContent = 'Refreshing…';
  navigator.geolocation.getCurrentPosition(
    pos => { state.lat = pos.coords.latitude; state.lon = pos.coords.longitude; reverseGeocode(state.lat, state.lon); loadWeather(true); },
    () => showToast('Could not get location', 'warning')
  );
}

async function reverseGeocode(lat, lon) {
  try {
    const r = await apiFetch(`/api/location/reverse-geocode?lat=${lat}&lon=${lon}`);
    if (r?.location) {
      state.location = r.location;
      const loc = r.location;
      const name = [loc.village, loc.district, loc.state].filter(Boolean).join(', ');
      document.getElementById('loc-name').textContent = name || 'Location detected';
      updateChatContext();

      // Load nearby mandis
      loadNearbyMandis(lat, lon);
    }
  } catch {}
}

async function loadNearbyMandis(lat, lon) {
  try {
    const r = await apiFetch(`/api/location/nearby-mandis?lat=${lat}&lon=${lon}&limit=3`);
    if (r?.mandis?.length) {
      const nearest = r.mandis[0];
      document.getElementById('pool-distance').textContent = `${nearest.distance_km} km`;
      // Update market dropdown to nearest mandi
      const sel = document.getElementById('market-select');
      if (sel) {
        const opt = [...sel.options].find(o => o.text === nearest.name);
        if (opt) sel.value = nearest.name;
      }
    }
  } catch {}
}

// ── Weather ───────────────────────────────────────────────────────────────────
async function loadWeather(force = false) {
  const lat = state.lat || 19.9975;
  const lon = state.lon || 73.7898;

  try {
    const data = await apiFetch(`/api/weather/current?lat=${lat}&lon=${lon}`);
    if (!data) return;

    state.weather = data;

    // Update sidebar widget
    document.getElementById('weather-icon').textContent = data.icon || '🌡️';
    document.getElementById('weather-temp').textContent = `${data.temperature_c}°C`;
    document.getElementById('weather-desc').textContent = data.description || '';
    document.getElementById('weather-hum').textContent = `${data.humidity_pct}% humidity`;

    // Update weather section
    renderWeatherSection(data);

    // Show weather note in crop AI
    const note = document.getElementById('crop-weather-note');
    const noteText = document.getElementById('crop-weather-note-text');
    if (note && noteText) {
      noteText.textContent = `Using live weather: ${data.temperature_c}°C, ${data.humidity_pct}% humidity, ${data.rainfall_mm}mm rain`;
      note.style.display = 'flex';
    }

    // Show spoilage auto-fill
    const spFill = document.getElementById('sp-weather-fill');
    if (spFill) spFill.style.display = 'flex';

    updateChatContext();

    // Show alert if any
    if (data.alert && force) showToast(data.alert, 'warning');
  } catch (e) {
    console.warn('Weather load failed:', e);
  }
}

function applyWeatherToSpoilage() {
  if (!state.weather) return;
  document.getElementById('sp-temp').value = state.weather.temperature_c;
  document.getElementById('sp-hum').value = state.weather.humidity_pct;
  showToast('Auto-filled from real-time weather ✓', 'success');
}

function renderWeatherSection(data) {
  const main = document.getElementById('weather-main-card');
  if (!main) return;
  main.innerHTML = `
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;">
      <div style="font-size:56px;line-height:1;">${data.icon || '🌡️'}</div>
      <div>
        <div style="font-family:'Outfit',sans-serif;font-size:48px;font-weight:900;line-height:1;color:var(--text);">${data.temperature_c}°<span style="font-size:22px;color:var(--text-sec);">C</span></div>
        <div style="font-size:14px;font-weight:600;color:var(--text-sec);margin-top:4px;">${data.description || ''}</div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">${data.city || ''} · Feels like ${data.feels_like_c || '--'}°C</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
      ${[
        ['💧', 'Humidity', `${data.humidity_pct}%`],
        ['🌬️', 'Wind', `${data.wind_kmh} km/h`],
        ['🌧️', 'Rainfall', `${data.rainfall_mm} mm`],
      ].map(([icon, label, val]) => `
        <div style="padding:10px;background:var(--bg);border-radius:var(--r-md);text-align:center;">
          <div style="font-size:20px;">${icon}</div>
          <div style="font-size:11px;color:var(--text-muted);">${label}</div>
          <div style="font-weight:700;font-size:14px;">${val}</div>
        </div>`).join('')}
    </div>
    ${data.alert ? `<div class="alert-box warning" style="margin-top:14px;"><div class="alert-icon">⚠️</div><div><div class="alert-title">Weather Alert</div><div class="alert-desc">${data.alert}</div></div></div>` : ''}
    <div style="font-size:11px;color:var(--text-muted);margin-top:12px;">Source: ${data.source === 'openweathermap' ? 'OpenWeatherMap API' : 'Seasonal estimate'} · ${data.updated_at || ''}</div>
  `;

  // Advice
  const adviceList = document.getElementById('weather-advice-list');
  if (adviceList) {
    const advice = [];
    if (data.temperature_c > 36) advice.push(['⚠️', 'Extreme heat', 'Irrigate at 5–7am and 6–8pm only. Mulch soil to lock in moisture.', 'warning']);
    else if (data.temperature_c > 30) advice.push(['☀️', 'High temperature', 'Increase irrigation frequency, monitor for heat stress.', 'info']);
    if (data.humidity_pct > 80 && data.rainfall_mm > 5) advice.push(['🍄', 'Fungal risk', 'Apply copper fungicide — ideal conditions for blight and mildew on tomato/onion.', 'warning']);
    if (data.rainfall_mm > 20) advice.push(['🌧️', 'Heavy rain', 'Check field drainage. Hold chemical spraying for 48h after rain.', 'info']);
    if (advice.length === 0) advice.push(['✅', 'Good conditions', 'Weather is favorable for most crops. Continue normal practices.', 'success']);

    adviceList.innerHTML = advice.map(([icon, title, desc, type]) => `
      <div class="alert-box ${type}" style="margin-bottom:10px;">
        <div class="alert-icon">${icon}</div>
        <div><div class="alert-title">${title}</div><div class="alert-desc">${desc}</div></div>
      </div>`).join('');
  }

  // Forecast
  const forecastRow = document.getElementById('weather-forecast-row');
  if (forecastRow && data.forecast_3d && Array.isArray(data.forecast_3d)) {
    forecastRow.innerHTML = data.forecast_3d.slice(0, 3).map(f => `
      <div class="card" style="text-align:center;background:var(--bg);">
        <div style="font-size:24px;margin-bottom:6px;">🌤️</div>
        <div style="font-weight:700;font-size:15px;">${f.day}</div>
        <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:800;">${Math.round(f.temp || 28)}°C</div>
        <div style="font-size:11px;color:var(--text-sec);">${f.desc || ''}</div>
        <div style="font-size:11px;color:var(--clr-info);margin-top:4px;">💧 ${Math.round(f.rain || 0)}% rain</div>
      </div>`).join('');
  }
}

// ── Crop AI ───────────────────────────────────────────────────────────────────
async function runCropAI() {
  const soil  = document.getElementById('crop-soil').value;
  const water = document.getElementById('crop-water').value;
  const land  = document.getElementById('crop-land').value;
  const season= document.getElementById('crop-season').value;

  if (!soil || !water || !land) {
    showToast('Please select all parameters before running the AI', 'warning');
    return;
  }

  const btn = document.getElementById('crop-run-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running XGBoost…';

  const area = document.getElementById('crop-result-area');
  area.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:12px;">
      ${[1,2,3].map(() => `
        <div class="skeleton" style="height:70px;border-radius:var(--r-md);"></div>`).join('')}
    </div>`;

  try {
    const body = { soil, water, land, season, region: state.location?.district || '' };
    if (state.weather) {
      body.temperature = state.weather.temperature_c;
      body.humidity    = state.weather.humidity_pct;
      body.rainfall    = state.weather.rainfall_mm;
    }

    const data = await apiFetch('/api/ml/crop-recommend', { method: 'POST', body: JSON.stringify(body) });
    if (!data?.results?.length) throw new Error('No results');

    document.getElementById('crop-model-badge').style.display = 'flex';

    area.innerHTML = data.results.slice(0, 5).map((r, i) => `
      <div class="card" style="padding:14px;border:${i === 0 ? '2px solid var(--clr-primary)' : '1px solid var(--border)'};transition:all .2s;margin-bottom:10px;" onmouseover="this.style.transform='translateX(4px)'" onmouseout="this.style.transform=''">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;">
          <div style="flex:1;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">
              ${i === 0 ? '<span class="badge badge-green">🏆 Top pick</span>' : `<span style="font-size:11px;font-weight:600;color:var(--text-muted);">#${i+1}</span>`}
              <span style="font-weight:700;font-size:15px;">${r.crop}</span>
              <span class="badge badge-${r.match === 'Excellent' ? 'green' : (r.match === 'Good' ? 'blue' : 'gray')}">${r.match}</span>
            </div>
            <div style="font-size:12px;color:var(--text-sec);margin-bottom:6px;">${r.reason || ''}</div>
          </div>
          <div style="text-align:right;flex-shrink:0;">
            <div style="font-family:'Outfit',sans-serif;font-size:22px;font-weight:800;color:var(--clr-primary);">${r.profit}</div>
            <div style="font-size:11px;color:var(--text-muted);">per acre estimate</div>
            <div style="font-size:13px;font-weight:700;color:var(--text);margin-top:2px;">AI Score: ${r.score}/10</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;margin-top:6px;">
          <div style="flex:1;height:6px;background:var(--border-light);border-radius:var(--r-full);overflow:hidden;">
            <div style="height:100%;width:${Math.min(100, r.confidence || 0)}%;background:${i === 0 ? 'var(--clr-primary)' : '#6B7280'};border-radius:var(--r-full);transition:width .8s ease;"></div>
          </div>
          <span style="font-size:11px;font-weight:600;color:var(--text-muted);">${r.confidence}% confidence</span>
        </div>
      </div>`).join('');

    if (data.supply_balance_note) {
      area.innerHTML += `<div class="info-well" style="margin-top:8px;"><i class="fa-solid fa-chart-bar"></i> ${data.supply_balance_note}</div>`;
    }

    showToast(`AI recommends ${data.results[0].crop} for your farm!`, 'success');
  } catch (e) {
    area.innerHTML = `<div class="alert-box danger"><div class="alert-icon">⚠️</div><div><div class="alert-title">Error</div><div class="alert-desc">${e.message || 'Failed to get recommendations'}</div></div></div>`;
    showToast('Crop AI error: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-microchip"></i> Run AI Recommendation';
  }
}

// ── Market Prices ─────────────────────────────────────────────────────────────
async function loadMarket() {
  const market = document.getElementById('market-select')?.value || 'Pune APMC';
  const grid = document.getElementById('market-grid');
  if (grid) grid.innerHTML = `${[1,2,3,4,5,6].map(() => '<div class="market-card skeleton" style="height:120px;"></div>').join('')}`;

  try {
    const data = await apiFetch(`/api/market/prices?market=${encodeURIComponent(market)}`);
    if (!data?.prices) throw new Error('No prices');
    state.mandiPrices = data.prices;

    if (grid) {
      grid.innerHTML = data.prices.map(p => `
        <div class="market-card" onclick="loadPriceChart('${p.crop}')">
          <div class="market-emoji">${p.emoji}</div>
          <div class="market-crop">${p.crop}</div>
          <div class="market-price">₹${p.price_per_kg}<span style="font-size:13px;font-weight:500;color:var(--text-sec);">/kg</span></div>
          <div class="market-change ${p.trend}">
            ${p.trend === 'up' ? '▲' : (p.trend === 'down' ? '▼' : '→')} ${Math.abs(p.week_change_pct)}% this week
          </div>
          <span class="market-signal ${p.selling_signal?.toLowerCase() || 'hold'}">${p.selling_signal}</span>
        </div>`).join('');
    }

    const upd = document.getElementById('market-updated');
    if (upd) upd.textContent = `Updated: ${data.updated_at} · ${market} · ${data.prices.length} crops`;

    // Update KPI
    const topRising = data.prices.filter(p => p.trend === 'up').sort((a,b) => b.week_change_pct - a.week_change_pct)[0];
    if (topRising) {
      const kpiDemand = document.getElementById('kpi-demand');
      const kpiChange = document.getElementById('kpi-demand-change');
      if (kpiDemand) kpiDemand.textContent = `${topRising.emoji} ${topRising.crop} ↑`;
      if (kpiChange) kpiChange.textContent = `▲ +${topRising.week_change_pct?.toFixed(1)}% this week`;
    }

    // Update chat context
    updateChatContext();
  } catch (e) {
    if (grid) grid.innerHTML = `<div style="grid-column:1/-1;padding:24px;text-align:center;color:var(--text-muted);">Failed to load prices. <button class="btn btn-ghost btn-sm" onclick="loadMarket()">Retry</button></div>`;
  }
}

async function loadPriceChart(crop) {
  try {
    const data = await apiFetch(`/api/market/price-history/${encodeURIComponent(crop)}`);
    if (!data?.prices) return;

    document.getElementById('market-chart-card').style.display = 'block';
    document.getElementById('chart-crop-name').textContent = `${data.emoji || ''} ${crop}`;

    const ctx = document.getElementById('price-chart').getContext('2d');
    if (state.priceChart) state.priceChart.destroy();

    state.priceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.prices.map(p => {
          const d = new Date(p.date);
          return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
        }),
        datasets: [{
          label: `${crop} ₹/kg`,
          data: data.prices.map(p => p.price),
          borderColor: '#16A34A',
          backgroundColor: 'rgba(22,163,74,0.08)',
          fill: true,
          tension: 0.4,
          pointRadius: 2,
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => `₹${ctx.raw}/kg` } } },
        scales: {
          y: { ticks: { callback: v => `₹${v}` }, grid: { color: 'rgba(0,0,0,.04)' } },
          x: { grid: { display: false } }
        }
      }
    });
  } catch(e) { console.error(e); }
}

// ── Transport Pool ────────────────────────────────────────────────────────────
const FARMERS = [
  { name: 'Raju Patil', crop: 'Tomato', acres: 3, dist: 0.8, color: '#16A34A', lat: 0.01, lon: 0.01 },
  { name: 'Savita Kale', crop: 'Onion', acres: 2, dist: 1.2, color: '#7C3AED', lat: -0.01, lon: 0.02 },
  { name: 'Mohan Jadhav', crop: 'Potato', acres: 5, dist: 2.1, color: '#D97706', lat: 0.02, lon: -0.01 },
  { name: 'Asha More', crop: 'Wheat', acres: 4, dist: 1.6, color: '#2563EB', lat: -0.02, lon: -0.02 },
  { name: 'Suresh Desai', crop: 'Brinjal', acres: 2, dist: 0.6, color: '#DC2626', lat: 0.015, lon: -0.015 },
  { name: 'Priya Bhosale', crop: 'Chilli', acres: 1.5, dist: 2.4, color: '#DB2777', lat: -0.015, lon: 0.015 },
];

function generateFarmerCards() {
  const grid = document.getElementById('farmer-grid');
  if (!grid) return;
  grid.innerHTML = FARMERS.map((f, i) => `
    <div class="farmer-card" id="farmer-${i}" onclick="toggleFarmer(${i}, this)">
      <div class="farmer-avatar-lg" style="background:${f.color};">${f.name[0]}</div>
      <div class="farmer-name-sm">${f.name}</div>
      <div class="farmer-meta">${f.crop} · ${f.acres}ac</div>
      <div class="farmer-dist">${f.dist} km away</div>
    </div>`).join('');
}

function toggleFarmer(idx, el) {
  if (state.selectedFarmers.has(idx)) {
    state.selectedFarmers.delete(idx);
    el.classList.remove('selected');
  } else {
    state.selectedFarmers.add(idx);
    el.classList.add('selected');
  }
  const badge = document.getElementById('selected-count-badge');
  if (badge) badge.textContent = `${state.selectedFarmers.size} selected`;
}

async function calcPool() {
  if (state.selectedFarmers.size === 0) {
    showToast('Please select at least one farmer', 'warning');
    return;
  }
  const btn = document.getElementById('pool-calc-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Calculating…';

  try {
    const data = await apiFetch('/api/ml/pool-calculate', {
      method: 'POST',
      body: JSON.stringify({
        farmer_count: state.selectedFarmers.size,
        total_weight_tons: (state.selectedFarmers.size + 1) * 2.5,
        distance_km: 25,
      })
    });

    document.getElementById('pool-placeholder').style.display = 'none';
    const result = document.getElementById('pool-result');
    result.style.display = 'block';
    result.innerHTML = `
      <div class="grid-2">
        <div style="padding:14px;background:var(--clr-danger-l);border-radius:var(--r-md);border:1px solid rgba(220,38,38,.2);text-align:center;">
          <div style="font-size:11px;color:var(--clr-danger);font-weight:600;text-transform:uppercase;">Individual cost</div>
          <div style="font-family:'Outfit',sans-serif;font-size:28px;font-weight:900;color:var(--clr-danger);">₹${data.individual_cost?.toLocaleString()}</div>
        </div>
        <div style="padding:14px;background:var(--clr-primary-xl);border-radius:var(--r-md);border:1px solid rgba(22,163,74,.2);text-align:center;">
          <div style="font-size:11px;color:var(--clr-primary);font-weight:600;text-transform:uppercase;">Pooled cost</div>
          <div style="font-family:'Outfit',sans-serif;font-size:28px;font-weight:900;color:var(--clr-primary);">₹${data.pooled_cost?.toLocaleString()}</div>
        </div>
      </div>
      <div style="padding:14px;background:var(--bg);border-radius:var(--r-md);margin-top:10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
        <div style="font-size:13px;color:var(--text-sec);">${data.total_farmers} farmers · ${data.distance_km}km</div>
        <div style="font-family:'Outfit',sans-serif;font-size:18px;font-weight:800;color:var(--clr-primary);">You save <span style="color:var(--clr-primary);">₹${data.savings?.toLocaleString()}</span></div>
        <span class="badge badge-green">-${data.savings_pct}%</span>
      </div>
      <div class="info-well" style="margin-top:10px;">
        <i class="fa-solid fa-leaf"></i> 🌿 CO₂ saved: ${data.co2_saved_kg} kg (= ${data.co2_saved_trees} trees planted)
      </div>`;

    showToast(`Save ₹${data.savings?.toLocaleString()} with pooled transport! 🎉`, 'success');
    updateTransportMap();
  } catch (e) {
    showToast('Pool calculation failed', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-truck"></i> Calculate Shared Transport';
  }
}

// ── Spoilage ──────────────────────────────────────────────────────────────────
async function runSpoilage() {
  const btn = document.getElementById('sp-run-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Predicting…';

  const area = document.getElementById('sp-result-area');
  area.innerHTML = '<div class="skeleton" style="height:200px;border-radius:var(--r-md);"></div>';

  try {
    const data = await apiFetch('/api/ml/spoilage-risk', {
      method: 'POST',
      body: JSON.stringify({
        crop:          document.getElementById('sp-crop').value,
        weight_tons:   parseFloat(document.getElementById('sp-weight').value) || 2.4,
        transit_hours: parseFloat(document.getElementById('sp-transit').value) || 6,
        temperature_c: parseFloat(document.getElementById('sp-temp').value) || 32,
        humidity_pct:  parseFloat(document.getElementById('sp-hum').value) || 72,
        packaging:     document.getElementById('sp-packaging').value,
      })
    });

    const riskColors = { low:'var(--clr-primary)', medium:'var(--clr-warn)', high:'#F97316', critical:'var(--clr-danger)' };
    const riskBg = { low:'var(--clr-primary-xl)', medium:'var(--clr-warn-l)', high:'rgba(249,115,22,.1)', critical:'var(--clr-danger-l)' };
    const color = riskColors[data.risk_level] || 'gray';
    const bg = riskBg[data.risk_level] || 'var(--bg)';

    area.innerHTML = `
      <div style="padding:16px;background:${bg};border-radius:var(--r-md);border:1.5px solid ${color};margin-bottom:14px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
          <div style="font-weight:700;font-size:16px;text-transform:capitalize;">Risk: ${data.risk_level?.toUpperCase()}</div>
          <div style="font-family:'Outfit',sans-serif;font-size:32px;font-weight:900;color:${color};">${data.risk_score}%</div>
        </div>
        <div style="height:10px;background:var(--border-light);border-radius:var(--r-full);overflow:hidden;margin-bottom:8px;">
          <div style="height:100%;width:${data.risk_score}%;background:${color};border-radius:var(--r-full);transition:width .8s;"></div>
        </div>
        <div style="font-size:12px;color:var(--text-sec);">${data.confidence}% model confidence · ${data.model}</div>
      </div>
      <div style="font-weight:600;font-size:13px;margin-bottom:10px;">Recommendations:</div>
      ${(data.suggestions || []).map(s => `
        <div style="display:flex;align-items:flex-start;gap:8px;padding:8px 0;border-bottom:1px solid var(--border-light);font-size:13px;">
          <span style="flex-shrink:0;">${s.split(' ')[0]}</span>
          <span style="color:var(--text-sec);">${s.split(' ').slice(1).join(' ')}</span>
        </div>`).join('')}`;

    showToast(`Spoilage risk: ${data.risk_level?.toUpperCase()} (${data.risk_score}%)`, data.risk_level === 'low' ? 'success' : 'warning');
  } catch(e) {
    area.innerHTML = `<div class="alert-box danger"><div class="alert-icon">⚠️</div><div><div class="alert-title">Error</div><div class="alert-desc">${e.message}</div></div></div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Predict Spoilage Risk';
  }
}

// ── Supply Balancer ───────────────────────────────────────────────────────────
async function runSupplyBalancer() {
  const region = document.getElementById('supply-region')?.value || 'Maharashtra';
  const area = document.getElementById('supply-result');
  const scoreBox = document.getElementById('supply-score-box');
  area.innerHTML = '<div style="text-align:center;padding:24px;"><i class="fa-solid fa-spinner fa-spin" style="font-size:24px;color:var(--clr-primary);"></i><div style="margin-top:8px;color:var(--text-sec);">AI crunching entropy optimization…</div></div>';

  try {
    const data = await apiFetch('/api/ml/supply-balance', {
      method: 'POST',
      body: JSON.stringify({ region, season: 'kharif' })
    });

    area.innerHTML = `
      <div style="overflow-x:auto;">
        <table class="data-table">
          <thead>
            <tr>
              <th>Village</th><th>District</th><th>AI Crop</th><th>AI Score</th>
              <th>Overproduction Risk</th><th>Profit/Acre</th><th>Reason</th>
            </tr>
          </thead>
          <tbody>
            ${data.assignments.map((a, i) => `
              <tr class="${i < 2 ? 'row-best' : ''}">
                <td><b>${a.village}</b></td>
                <td>${a.district}</td>
                <td style="font-weight:700;color:var(--clr-primary);">${a.assigned_crop}</td>
                <td><span style="font-family:'Outfit',sans-serif;font-weight:800;">${a.ai_score}</span>/10</td>
                <td>
                  <div style="display:flex;align-items:center;gap:6px;">
                    <div style="width:60px;height:6px;background:var(--border-light);border-radius:var(--r-full);overflow:hidden;">
                      <div style="height:100%;width:${Math.min(100, a.overproduction_risk * 100)}%;background:${a.overproduction_risk > 0.5 ? 'var(--clr-danger)' : (a.overproduction_risk > 0.25 ? 'var(--clr-warn)' : 'var(--clr-primary)')};"></div>
                    </div>
                    <span style="font-size:11px;">${Math.round(a.overproduction_risk * 100)}%</span>
                  </div>
                </td>
                <td style="font-weight:600;color:var(--clr-primary);">${a.expected_profit}</td>
                <td style="font-size:11px;color:var(--text-sec);max-width:200px;">${a.reason?.split(' · ')[0] || ''}</td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>`;

    scoreBox.style.display = 'flex';
    scoreBox.innerHTML = `
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:14px;background:var(--bg);border-radius:var(--r-md);font-size:13px;">
        <div>Unique crops: <b>${data.unique_crops?.length}</b></div>
        <div>Total farmers: <b>${data.total_farmers?.toLocaleString()}</b></div>
        <div>Balance score: <b style="color:var(--clr-primary);">${data.balance_score}%</b></div>
        <span class="badge ${data.balance_grade === 'Excellent' ? 'badge-green' : 'badge-amber'}">${data.balance_grade}</span>
        <div style="font-size:11px;color:var(--text-muted);margin-left:auto;">${data.model}</div>
      </div>`;

    showToast(`Balancer complete — ${data.balance_grade} distribution across ${data.assignments.length} villages`, 'success');
  } catch(e) {
    area.innerHTML = `<div class="alert-box danger"><div class="alert-icon">⚠️</div><div>${e.message}</div></div>`;
  }
}

// ── Chat Context ──────────────────────────────────────────────────────────────
function updateChatContext() {
  const ctxLoc = document.getElementById('ctx-location');
  const ctxWeath = document.getElementById('ctx-weather');
  const ctxPrices = document.getElementById('ctx-prices');

  if (ctxLoc && state.location) {
    ctxLoc.textContent = `${state.location.village || ''}, ${state.location.district || ''}, ${state.location.state || ''}`;
  }
  if (ctxWeath && state.weather) {
    ctxWeath.textContent = `${state.weather.temperature_c}°C · ${state.weather.humidity_pct}% humidity · ${state.weather.description}`;
  }
  if (ctxPrices && state.mandiPrices.length) {
    const top = state.mandiPrices.slice(0, 3).map(p => `${p.crop} ₹${p.price_per_kg}/kg`).join(' · ');
    ctxPrices.textContent = top;
  }
}

// ── Dashboard Bars animate ────────────────────────────────────────────────────
function animateBars() {
  document.querySelectorAll('.bar-fill').forEach(el => {
    const w = el.getAttribute('data-width');
    if (w) el.style.width = w + '%';
  });
}

// ── Supply map (for dashboard) ────────────────────────────────────────────────
let _dashMap;
function initSupplyMap() {
  if (_dashMap) return;
  const container = document.getElementById('dash-map');
  if (!container) return;
  const lat = state.lat || 19.9975, lon = state.lon || 73.7898;
  _dashMap = L.map('dash-map', { zoomControl: false }).setView([lat, lon], 8);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap', maxZoom: 18
  }).addTo(_dashMap);

  const colors = ['#16A34A','#D97706','#2563EB','#DC2626','#7C3AED','#DB2777'];
  const villages = [
    ['Nashik', 20.0, 73.8, 'Tomato'], ['Pune', 18.5, 73.8, 'Potato'],
    ['Ahmednagar', 19.1, 74.7, 'Onion'], ['Solapur', 17.7, 75.9, 'Soybean'],
    ['Satara', 17.7, 74.0, 'Brinjal'], ['Aurangabad', 19.9, 75.3, 'Wheat'],
  ];
  villages.forEach(([name, vlat, vlon, crop], i) => {
    L.circleMarker([vlat, vlon], {
      radius: 12,
      fillColor: colors[i % colors.length],
      color: '#fff',
      weight: 2,
      fillOpacity: 0.85
    }).addTo(_dashMap).bindPopup(`<b>${name}</b><br>AI crop: ${crop}`);
  });
}

// ── API Helper ────────────────────────────────────────────────────────────────
async function apiFetch(url, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (TOKEN()) headers['Authorization'] = `Bearer ${TOKEN()}`;
  if (opts.body && typeof opts.body !== 'string') opts.body = JSON.stringify(opts.body);

  const r = await fetch(API + url, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
  if (r.status === 401) { logout(); return; }
  const ct = r.headers.get('content-type') || '';
  if (ct.includes('json')) return r.json();
  return null;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(t);
  requestAnimationFrame(() => { t.classList.add('show'); });
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 400); }, 3500);
}

// ── Init maps on section switch ───────────────────────────────────────────────
window.addEventListener('load', () => {
  setTimeout(() => initSupplyMap(), 800);
});
