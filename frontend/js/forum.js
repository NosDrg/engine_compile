// frontend/js/forum.js
import { api } from './api.js';
import { refreshUser, renderNavAuth } from './auth.js';

document.addEventListener('DOMContentLoaded', async () => {
  const user = await refreshUser();
  renderNavAuth(user);
  if (!user) { location.href = '/login.html?redirect=/forum.html'; return; }
  const chat = document.getElementById('chat');
  const state = document.getElementById('state');
  const olderButton = document.getElementById('load-older');
  const seen = new Set();
  const deletedMessageIds = new Set();
  let oldestId = null;
  let newestId = null;
  let deletionCursor = 0;

  function makeRow(message) {
    const row = document.createElement('article');
    row.className = 'msg';
    row.dataset.messageId = message.id;
    const meta = document.createElement('small');
    meta.textContent = (message.display_name || message.username) + ' · ' + (message.created_at || '');
    const body = document.createElement('p');
    body.textContent = message.body;
    row.append(meta, body);
    return row;
  }

  function append(message) {
    if (!message || seen.has(message.id) || deletedMessageIds.has(message.id)) return;
    seen.add(message.id);
    chat.append(makeRow(message));
    if (oldestId === null || message.id < oldestId) oldestId = message.id;
    if (newestId === null || message.id > newestId) newestId = message.id;
    chat.scrollTop = chat.scrollHeight;
  }

  try {
    const { messages } = await api.forumMessages();
    if (Array.isArray(messages)) {
      messages.forEach(append);
      olderButton.hidden = messages.length < 100;
    }
  } catch (error) { state.textContent = error.message; }

  // Polling đồng bộ tin nhắn
  setInterval(async () => {
    try {
      const afterMessageId = newestId ?? 0;
      const [{ messages }, { deletions }] = await Promise.all([
        api.forumMessages(undefined, afterMessageId), api.forumDeletions(deletionCursor),
      ]);
      if (Array.isArray(messages)) messages.forEach(append);
      if (Array.isArray(deletions)) {
        deletions.forEach((deletion) => {
          deletedMessageIds.add(deletion.message_id);
          deletionCursor = Math.max(deletionCursor, deletion.id);
          chat.querySelector('[data-message-id="' + deletion.message_id + '"]')?.remove();
        });
      }
    } catch { /* Bỏ qua gián đoạn mạng tạm thời */ }
  }, 2500);

  olderButton.addEventListener('click', async () => {
    if (oldestId === null) return;
    olderButton.disabled = true;
    const oldHeight = chat.scrollHeight;
    const oldTop = chat.scrollTop;
    try {
      const { messages } = await api.forumMessages(oldestId);
      if (Array.isArray(messages)) {
        const fragment = document.createDocumentFragment();
        messages.forEach((message) => {
          if (seen.has(message.id) || deletedMessageIds.has(message.id)) return;
          seen.add(message.id);
          fragment.append(makeRow(message));
          if (oldestId === null || message.id < oldestId) oldestId = message.id;
        });
        chat.prepend(fragment);
        chat.scrollTop = oldTop + chat.scrollHeight - oldHeight;
        olderButton.hidden = messages.length < 100;
      }
    } catch (error) { state.textContent = error.message; }
    finally { olderButton.disabled = false; }
  });

  let socket = null;
  let retry = 0;
  let reconnectTimer = null;

  function connect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(scheme + '//' + location.host + '/api/forum/ws');

    socket.onopen = () => {
      retry = 0;
      state.textContent = 'Đang trực tuyến';
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'message') append(data.message);
        else if (data.type === 'deleted') {
          deletedMessageIds.add(Number(data.id));
          chat.querySelector('[data-message-id="' + data.id + '"]')?.remove();
        }
        else if (data.type === 'error') state.textContent = data.message;
      } catch (err) {
        console.warn('Frame WS không phải JSON hợp lệ:', event.data);
      }
    };

    socket.onclose = () => {
      state.textContent = 'Mất kết nối; đang thử kết nối lại…';
      const delay = Math.min(15000, 1000 * Math.pow(2, Math.min(retry++, 4)));
      reconnectTimer = setTimeout(connect, delay);
    };

    socket.onerror = () => {
      try { socket.close(); } catch (_) {}
    };
  }

  connect();

  document.getElementById('compose').addEventListener('submit', (event) => {
    event.preventDefault();
    const input = document.getElementById('message');
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      state.textContent = 'Chưa kết nối được diễn đàn.';
      return;
    }
    const text = input.value.trim();
    if (!text) return;
    socket.send(JSON.stringify({ body: text }));
    input.value = '';
  });
});