/* ===== AgriNet AI — Sidebar & UI Controller ===== */

// ---- Sidebar Tab Switching ----
function switchTab(tab) {
  document.querySelectorAll('.sidebar-nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  const sec = document.getElementById('s-' + tab);
  if (sec) { sec.classList.add('active'); animateBars(); }
}

document.addEventListener('DOMContentLoaded', () => {
  // Wire sidebar nav
  document.querySelectorAll('.sidebar-nav-item[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Live clock
  function updateClock() {
    const el = document.getElementById('topbar-time');
    if (el) {
      const now = new Date();
      el.textContent = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) + ' · 28°C';
    }
  }
  updateClock();
  setInterval(updateClock, 60000);

  // Populate user info
  try {
    const token = localStorage.getItem('agrinet_token');
    if (token) {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const name = payload.name || payload.username || 'Farmer';
      const email = payload.email || '';
      const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0,2);
      ['user-initials','user-initials-top'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = initials;
      });
      ['dropdown-name'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = name;
      });
      const em = document.getElementById('dropdown-email');
      if (em) em.textContent = email;
    }
  } catch(e) {}

  // Animate bars on load
  animateBars();
});

// ---- Mobile Sidebar Toggle ----
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar.classList.toggle('open');
  overlay.classList.toggle('show');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-overlay').classList.remove('show');
}

// ---- Theme Toggle ----
function toggleTheme() {
  const body = document.body;
  const isDark = body.dataset.theme === 'dark';
  body.dataset.theme = isDark ? 'light' : 'dark';
  localStorage.setItem('agrinet_theme', body.dataset.theme);
  const icon = document.getElementById('theme-icon');
  const label = document.getElementById('theme-label');
  if (icon) icon.className = isDark ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
  if (label) label.textContent = isDark ? 'Dark Mode' : 'Light Mode';
}

// Load saved theme
(function() {
  const saved = localStorage.getItem('agrinet_theme');
  if (saved) {
    document.body.dataset.theme = saved;
    const icon = document.getElementById('theme-icon');
    const label = document.getElementById('theme-label');
    if (saved === 'dark') {
      if (icon) icon.className = 'fa-solid fa-sun';
      if (label) label.textContent = 'Light Mode';
    }
  }
})();

// ---- User Menu ----
function toggleUserMenu() {
  document.getElementById('user-dropdown')?.classList.toggle('show');
}
document.addEventListener('click', (e) => {
  if (!e.target.closest('.sidebar-user') && !e.target.closest('#user-menu-top')) {
    document.getElementById('user-dropdown')?.classList.remove('show');
  }
});

// ---- Hero Chat ----
function heroChat() {
  const input = document.getElementById('hero-chat-input');
  if (!input || !input.value.trim()) return;
  switchTab('voice');
  const chatInput = document.getElementById('chat-input');
  if (chatInput) { chatInput.value = input.value; input.value = ''; sendChat(); }
}

// ---- Bar Animation ----
function animateBars() {
  setTimeout(() => {
    document.querySelectorAll('.bar-fill[data-width]').forEach(bar => {
      bar.style.width = bar.dataset.width + '%';
    });
  }, 100);
}

// ---- Logout ----
function logout() {
  localStorage.removeItem('agrinet_token');
  window.location.href = '/login.html';
}

// ── Read user from Supabase JWT (stored by login.html) ──────────
(function loadSupabaseUser() {
  try {
    const stored = localStorage.getItem('agrinet_user');
    if (stored) {
      const user = JSON.parse(stored);
      const name = user.name || user.email?.split('@')[0] || 'Farmer';
      const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0,2);
      ['user-initials','user-initials-top'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = initials;
      });
      const nameEl = document.getElementById('dropdown-name');
      if (nameEl) nameEl.textContent = name;
      const emailEl = document.getElementById('dropdown-email');
      if (emailEl) emailEl.textContent = user.email || '';
      return;
    }
    // Fallback: decode JWT
    const token = localStorage.getItem('agrinet_token');
    if (!token) return;
    const parts = token.split('.');
    if (parts.length < 2) return;
    const payload = JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')));
    const name = payload.name || payload.email?.split('@')[0] || 'Farmer';
    const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0,2);
    ['user-initials','user-initials-top'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = initials;
    });
  } catch(e) {}
})();

// ── Logout via Supabase ─────────────────────────────────────────
window.logout = async function() {
  localStorage.removeItem('agrinet_token');
  localStorage.removeItem('agrinet_user');
  // If Supabase client is loaded, also sign out from it
  try {
    const { createClient } = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm');
    const sb = createClient(
      'https://bkgvvwbukgfijamnkzsp.supabase.co',
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJrZ3Z2d2J1a2dmaWphbW5renNwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2MDg0MDcsImV4cCI6MjA5NTE4NDQwN30.WkqxWqJL4qVXNUnQMroNLfAQ188lyXlhNLhiOu0W3YU'
    );
    await sb.auth.signOut();
  } catch(e) {}
  window.location.href = '/login.html';
};
