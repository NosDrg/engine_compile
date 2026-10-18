import { api } from './api.js';
import { setUser } from './auth.js';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  const status = document.getElementById('login-status');
  const button = document.getElementById('btn-login');
  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    status.textContent = '';
    button.disabled = true;
    try {
      const result = await api.login(
        document.getElementById('login-username').value.trim(),
        document.getElementById('login-password').value,
        document.getElementById('remember-me')?.checked || false
      );
      setUser(result.user);
      const next = new URLSearchParams(location.search).get('redirect');
      location.href = next && next.startsWith('/') && !next.startsWith('//') ? next : '/arena.html';
    } catch (error) {
      status.textContent = error.message;
      status.className = 'alert alert-error show';
    } finally {
      button.disabled = false;
    }
  });
  document.getElementById('forgot-pwd')?.addEventListener('click', (event) => {
    event.preventDefault();
    status.textContent = 'Liên hệ quản trị viên để đặt lại mật khẩu.';
    status.className = 'alert alert-error show';
  });
});
