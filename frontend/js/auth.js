// frontend/js/auth.js
import { api } from './api.js';

const AUTH_KEY = 'bot_arena_user';

export function getUser() {
  try { 
    const raw = localStorage.getItem(AUTH_KEY); 
    return raw ? JSON.parse(raw) : null; 
  } catch { 
    return null; 
  }
}

export function setUser(user) {
  if (user) localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  else localStorage.removeItem(AUTH_KEY);
}

export async function refreshUser() {
  try { 
    const response = await api.me(); 
    setUser(response.user); 
    return response.user; 
  } catch { 
    setUser(null); 
    return null; 
  }
}

export async function logout() {
  try { await api.logout(); } catch { }
  setUser(null);
  window.location.href = '/login.html';
}

// frontend/js/auth.js

export function renderNavAuth(user = getUser()) {
  const actions = document.getElementById('navbar-actions');
  if (!actions) return;

  if (user) {
    const extraLinks = Array.isArray(user.extra_nav) 
      ? user.extra_nav.map(item => 
          `<a href="${escapeHtml(item.path)}" class="nav-user-menu-link">${escapeHtml(item.title)}</a>`
        ).join('')
      : (user.role === 'admin' ? '<a href="admin/admin.html" class="nav-user-menu-link">Quản trị viên</a>' : '');

    actions.innerHTML = `
      <div class="nav-user-dropdown" id="nav-user-dropdown-wrap">
        <button class="nav-user-btn" id="nav-user-toggle" type="button" aria-expanded="false">
          <span class="user-name-text">${escapeHtml(user.display_name || user.username)}</span>
          <span class="nav-caret">▾</span>
        </button>

        <!-- THANH TASKBAR MENU DỌC -->
        <div class="nav-taskbar-vertical" id="nav-user-menu" hidden>
          <a href="/profile.html" class="taskbar-item">Hồ sơ</a>
          <a href="/missions.html" class="taskbar-item">Nhiệm vụ</a>
          <a href="/forum.html" class="taskbar-item">Diễn đàn</a>
          <a href="/notifications.html" class="taskbar-item" id="nav-notifications">
            <span>Thông báo</span>
            <span class="taskbar-badge" id="nav-notification-count" hidden></span>
          </a>
          ${extraLinks}
          <div class="taskbar-divider"></div>
          <button class="taskbar-item taskbar-logout" id="btn-nav-logout" type="button">Đăng xuất</button>
        </div>
      </div>
    `;

    // Sự kiện click bật/tắt thanh taskbar dọc
    const toggleBtn = document.getElementById('nav-user-toggle');
    const menuEl = document.getElementById('nav-user-menu');

    toggleBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      const isHidden = menuEl.hasAttribute('hidden');
      if (isHidden) {
        menuEl.removeAttribute('hidden');
        toggleBtn.setAttribute('aria-expanded', 'true');
      } else {
        menuEl.setAttribute('hidden', '');
        toggleBtn.setAttribute('aria-expanded', 'false');
      }
    });

    document.getElementById('btn-nav-logout')?.addEventListener('click', logout);
    if (typeof refreshNotificationBadge === 'function') refreshNotificationBadge();
  } else {
    actions.innerHTML = `
      <a href="/login.html" class="btn btn-ghost btn-sm">Đăng nhập</a>
      <a href="/register.html" class="btn btn-primary btn-sm">Đăng ký</a>
    `;
  }
}

function closeNavUserMenu() {
  const toggle = document.getElementById('nav-user-toggle');
  const menu = document.getElementById('nav-user-menu');
  if (!toggle || !menu) return;
  toggle.setAttribute('aria-expanded', 'false');
  menu.hidden = true;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

document.addEventListener('DOMContentLoaded', async () => {
  renderNavAuth(await refreshUser());
  setInterval(refreshNotificationBadge, 30000);
});

document.addEventListener('click', (event) => {
  if (event.target instanceof Element && !event.target.closest('.nav-user-dropdown')) {
    closeNavUserMenu();
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeNavUserMenu();
});

async function refreshNotificationBadge() {
  const link = document.getElementById('nav-notifications');
  const count = document.getElementById('nav-notification-count');
  if (!link || !count) return;
  try {
    const { unread_count } = await api.notifications();
    count.textContent = unread_count ? String(unread_count) : '';
    count.hidden = !unread_count;
  } catch { }
}