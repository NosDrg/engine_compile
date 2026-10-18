import { api } from './api.js';

const AUTH_KEY = 'bot_arena_user';
export function getUser() {
  try { const raw = localStorage.getItem(AUTH_KEY); return raw ? JSON.parse(raw) : null; }
  catch { return null; }
}
export function setUser(user) {
  if (user) localStorage.setItem(AUTH_KEY, JSON.stringify(user));
  else localStorage.removeItem(AUTH_KEY);
}
export async function refreshUser() {
  try { const response = await api.me(); setUser(response.user); return response.user; }
  catch { setUser(null); return null; }
}
export async function logout() {
  try { await api.logout(); } catch { /* session may already be expired */ }
  setUser(null);
  window.location.href = '/login.html';
}
export function renderNavAuth(user = getUser()) {
  const actions = document.getElementById('navbar-actions');
  if (!actions) return;
  if (user) {
    const admin = user.role === 'admin' ? '<a href="/admin/" class="btn btn-ghost btn-sm">Quản trị</a>' : '';
    actions.innerHTML = '<a class="nav-user" href="/profile.html">👤 <strong>' + escapeHtml(user.display_name || user.username) + '</strong></a>' +
      '<a href="/notifications.html" class="btn btn-ghost btn-sm" id="nav-notifications">Thông báo</a>' +
      '<a href="/missions.html" class="btn btn-ghost btn-sm">Nhiệm vụ</a>' +
      '<a href="/forum.html" class="btn btn-ghost btn-sm">Diễn đàn</a>' + admin + '<a href="/arena.html" class="btn btn-primary btn-sm">Thi đấu</a>' +
      '<button class="btn btn-ghost btn-sm" id="btn-nav-logout">Đăng xuất</button>';
    document.getElementById('btn-nav-logout')?.addEventListener('click', logout);
    refreshNotificationBadge();
  } else {
    actions.innerHTML = '<a href="/login.html" class="btn btn-ghost btn-sm">Đăng nhập</a><a href="/register.html" class="btn btn-primary btn-sm">Đăng ký</a>';
  }
}
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}
document.addEventListener('DOMContentLoaded', async () => {
  renderNavAuth(await refreshUser());
  setInterval(refreshNotificationBadge, 30000);
});

async function refreshNotificationBadge() {
  const link = document.getElementById('nav-notifications');
  if (!link) return;
  try {
    const { unread_count } = await api.notifications();
    link.textContent = unread_count ? 'Thông báo (' + unread_count + ')' : 'Thông báo';
  } catch { /* keep navigation available when notification service is offline */ }
}
