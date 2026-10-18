import { api } from './api.js';
import { setUser } from './auth.js';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('register-form');
  const status = document.getElementById('reg-status');
  const button = document.getElementById('btn-register');
  [
    ['toggle-pwd1', 'reg-password'],
    ['toggle-pwd2', 'reg-confirm']
  ].forEach(([toggleId, inputId]) => {
    const toggle = document.getElementById(toggleId);
    const input = document.getElementById(inputId);
    toggle?.addEventListener('click', () => {
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      toggle.textContent = visible ? '\u1ea8n' : 'Hi\u1ec7n';
      toggle.setAttribute('aria-pressed', String(visible));
    });
  });

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    status.textContent = '';
    const password = document.getElementById('reg-password').value;
    if (password.length < 12) {
      status.textContent = 'Mật khẩu cần ít nhất 12 ký tự.';
      return;
    }
    if (password !== document.getElementById('reg-confirm').value) {
      status.textContent = 'Mật khẩu xác nhận không khớp.';
      return;
    }
    if (!document.getElementById('agree-terms')?.checked) {
      status.textContent = 'Vui lòng đồng ý với điều khoản sử dụng.';
      return;
    }
    button.disabled = true;
    try {
      const result = await api.register({
        username: document.getElementById('reg-username').value.trim(),
        display_name: document.getElementById('reg-display').value.trim(),
        password,
        preferred_language: document.querySelector('input[name="preferred_lang"]:checked')?.value || 'python'
      });
      setUser(result.user);
      location.href = '/arena.html';
    } catch (error) {
      status.textContent = error.message;
      status.className = 'alert alert-error show';
    } finally {
      button.disabled = false;
    }
  });
});
