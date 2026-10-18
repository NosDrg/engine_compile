// frontend/js/toast.js — Shared toast notification utility
export function showToast(title, message = '', type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const bodyDiv = document.createElement('div');

  if (title) {
    const titleDiv = document.createElement('div');
    titleDiv.className = 'toast-title';
    titleDiv.textContent = title; // Chống XSS
    bodyDiv.appendChild(titleDiv);
  }

  if (message) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'toast-msg';
    msgDiv.textContent = message; // Chống XSS
    bodyDiv.appendChild(msgDiv);
  }

  toast.append(bodyDiv);
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideIn 0.25s ease reverse';
    setTimeout(() => toast.remove(), 240);
  }, duration);
}