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
