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
    meta.textContent = (message.display_name || message.username) + ' · ' + message.created_at;
    const body = document.createElement('p');
    body.textContent = message.body;
    row.append(meta, body);
    return row;
  }
  function append(message) {
    if (seen.has(message.id) || deletedMessageIds.has(message.id)) return;
    seen.add(message.id);
    chat.append(makeRow(message));
    if (oldestId === null || message.id < oldestId) oldestId = message.id;
    if (newestId === null || message.id > newestId) newestId = message.id;
    chat.scrollTop = chat.scrollHeight;
  }
  try {
    const { messages } = await api.forumMessages();
    messages.forEach(append);
    olderButton.hidden = messages.length < 100;
  } catch (error) { state.textContent = error.message; }

  // SQLite stores messages across API workers; polling lets clients connected
  // to different workers receive the same conversation without a broker.
  setInterval(async () => {
    try {
      const afterMessageId = newestId ?? 0;
      const [{ messages }, { deletions }] = await Promise.all([
        api.forumMessages(undefined, afterMessageId), api.forumDeletions(deletionCursor),
      ]);
      messages.forEach(append);
      deletions.forEach((deletion) => {
        deletedMessageIds.add(deletion.message_id);
        deletionCursor = Math.max(deletionCursor, deletion.id);
        chat.querySelector('[data-message-id="' + deletion.message_id + '"]')?.remove();
      });
    } catch { /* keep the WebSocket and composer usable during brief API outages */ }
  }, 2500);

  olderButton.addEventListener('click', async () => {
    if (oldestId === null) return;
    olderButton.disabled = true;
    const oldHeight = chat.scrollHeight;
    const oldTop = chat.scrollTop;
    try {
      const { messages } = await api.forumMessages(oldestId);
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
    } catch (error) { state.textContent = error.message; }
    finally { olderButton.disabled = false; }
  });

  let socket;
  let retry = 0;
  function connect() {
    const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(scheme + '//' + location.host + '/api/forum/ws');
    socket.onopen = () => { retry = 0; state.textContent = 'Đang trực tuyến'; };
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'message') append(data.message);
      else if (data.type === 'deleted') {
        deletedMessageIds.add(Number(data.id));
        chat.querySelector('[data-message-id="' + data.id + '"]')?.remove();
      }
      else if (data.type === 'error') state.textContent = data.message;
    };
    socket.onclose = () => {
      state.textContent = 'Mất kết nối; đang thử kết nối lại…';
      setTimeout(connect, Math.min(15000, 1000 * (2 ** retry++)));
    };
    socket.onerror = () => socket.close();
  }
  connect();
  document.getElementById('compose').addEventListener('submit', (event) => {
    event.preventDefault();
    const input = document.getElementById('message');
    if (!socket || socket.readyState !== WebSocket.OPEN) { state.textContent = 'Chưa kết nối được diễn đàn.'; return; }
    socket.send(JSON.stringify({ body: input.value }));
    input.value = '';
  });
});
