// frontend/js/notifications.js
import { api } from './api.js';
import { refreshUser, renderNavAuth } from './auth.js';

document.addEventListener('DOMContentLoaded', async () => {
  const user = await refreshUser(); 
  renderNavAuth(user);
  if (!user) { location.href = '/login.html?redirect=/notifications.html'; return; }

  const host = document.getElementById('notifications');
  const status = document.getElementById('status');

  async function load() {
    if (!host) return;
    try {
      const { notifications } = await api.notifications();
      host.replaceChildren();
      if (!notifications || !notifications.length) {
        if (status) status.textContent = 'Chưa có thông báo.';
        return;
      }
      if (status) status.textContent = '';

      for (const item of notifications) {
        const card = document.createElement('article');
        card.className = 'note' + (item.read_at ? '' : ' unread');

        const title = document.createElement('strong');
        title.textContent = item.title;

        const body = document.createElement('p');
        body.textContent = item.body;

        const date = document.createElement('small');
        date.textContent = item.created_at;

        card.append(title, body, date);

        if (!item.read_at) {
          const button = document.createElement('button');
          button.className = 'btn btn-ghost btn-sm';
          button.textContent = 'Đã đọc';
          button.addEventListener('click', async () => {
            await api.markNotificationsRead(item.id);
            await load();
          });
          card.append(button);
        }

        // Chống open-redirect an toàn
        if (item.href && item.href.startsWith('/') && !item.href.startsWith('//') && !item.href.includes('\\')) {
          const link = document.createElement('a');
          link.className = 'btn btn-ghost btn-sm';
          link.href = item.href;
          link.textContent = 'Mở';
          card.append(link);
        }

        host.append(card);
      }
    } catch (e) {
      if (status) status.textContent = e.message;
    }
  }

  // Thêm Optional Chaining ?. để không crash trang nếu thiếu nút
  document.getElementById('mark-all')?.addEventListener('click', async () => {
    try {
      await api.markNotificationsRead();
      await load();
    } catch (e) {
      if (status) status.textContent = e.message;
    }
  });

  await load();
});