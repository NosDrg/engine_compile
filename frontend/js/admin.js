import { api } from '../js/api.js';
import { refreshUser, renderNavAuth } from '../js/auth.js';

document.addEventListener('DOMContentLoaded', async () => {
  const status = document.getElementById('admin-status');
  const say = (text) => { status.textContent = text || ''; };
  const user = await refreshUser();
  renderNavAuth(user);
  if (!user || user.role !== 'admin') {
    location.href = '/login.html?redirect=/admin/';
    return;
  }

  async function loadOverview() {
    const { overview } = await api.adminOverview();
    document.getElementById('admin-overview').innerHTML = Object.entries(overview).map(([key, value]) =>
      '<article class="admin-card"><div class="admin-stat">' + Number(value).toLocaleString('vi-VN') +
      '</div><div>' + escapeHtml(key.replaceAll('_', ' ')) + '</div></article>').join('');
  }

  async function loadUsers() {
    const { users } = await api.adminUsers();
    const body = document.getElementById('admin-users');
    body.innerHTML = users.map((account) => '<tr><td>' + escapeHtml(account.display_name || account.username) +
      '<br><small>@' + escapeHtml(account.username) + '</small></td><td>' + escapeHtml(account.role) +
      '</td><td>' + account.rating + '</td><td>' + account.wins + ' / ' + account.losses + ' / ' + account.draws +
      '</td><td><button class="btn btn-ghost btn-sm" data-user="' + account.id + '" data-role="' +
      (account.role === 'admin' ? 'player' : 'admin') + '">' +
      (account.role === 'admin' ? 'Hạ quyền' : 'Cấp admin') + '</button> ' +
      '<button class="btn btn-ghost btn-sm" data-delete-user="' + account.id + '">Xoá tài khoản</button></td></tr>').join('');
    body.querySelectorAll('[data-user]').forEach((button) => button.addEventListener('click', async () => {
      try { await api.setRole(button.dataset.user, button.dataset.role); say('Đã cập nhật vai trò.'); await loadUsers(); }
      catch (error) { say(error.message); }
    }));
    users.forEach((account) => {
      const button = document.createElement('button');
      button.className = 'btn btn-ghost btn-sm';
      button.dataset.resetPassword = account.id;
      button.textContent = 'Đặt lại mật khẩu';
      const row = [...body.querySelectorAll('tr')].find((item) => item.querySelector('[data-user]')?.dataset.user === String(account.id));
      row?.lastElementChild?.prepend(button, ' ');
    });
    body.querySelectorAll('[data-reset-password]').forEach((button) => button.addEventListener('click', async () => {
      const account = users.find((item) => String(item.id) === button.dataset.resetPassword);
      if (!account) return;
      const password = window.prompt('Nhập mật khẩu mới cho @' + account.username + ' (ít nhất 12 ký tự):');
      if (password === null) return;
      if (password.length < 12) { say('Mật khẩu mới cần ít nhất 12 ký tự.'); return; }
      try { await api.resetUserPassword(account.id, password); say('Đã đổi mật khẩu và đăng xuất các phiên của tài khoản.'); }
      catch (error) { say(error.message); }
    }));
    body.querySelectorAll('[data-delete-user]').forEach((button) => button.addEventListener('click', async () => {
      const account = users.find((item) => String(item.id) === button.dataset.deleteUser);
      if (!account || !window.confirm('Xoá tài khoản @' + account.username + '? Mã bot, trận và tin nhắn gắn với tài khoản này cũng bị xoá.')) return;
      try { await api.deleteUser(account.id); say('Đã xoá tài khoản và dữ liệu liên quan.'); await Promise.all([loadUsers(), loadOverview(), loadSubmissions()]); }
      catch (error) { say(error.message); }
    }));
  }

  async function loadSubmissions() {
    const { submissions } = await api.adminSubmissions();
    const body = document.getElementById('admin-submissions');
    body.innerHTML = submissions.map((item) => '<tr><td>@' + escapeHtml(item.username) + '</td><td>' + escapeHtml(item.version_name) +
      '</td><td>' + escapeHtml(item.language) + '</td><td>' + escapeHtml(item.status) + (item.is_active ? ' · đang dùng' : '') +
      '</td><td>' + escapeHtml(item.created_at) + '</td><td><button class="btn btn-ghost btn-sm" data-delete-sub="' + escapeHtml(item.id) + '">Xoá code</button></td></tr>').join('');
    body.querySelectorAll('[data-delete-sub]').forEach((button) => button.addEventListener('click', async () => {
      if (!window.confirm('Xóa toàn bộ mã nguồn và log lỗi của phiên bản bot này? Kết quả trận và replay vẫn được giữ.')) return;
      try { await api.deleteSubmission(button.dataset.deleteSub); say('Đã xóa mã nguồn; kết quả trận và replay được giữ lại.'); await Promise.all([loadSubmissions(), loadOverview()]); }
      catch (error) { say(error.message); }
    }));
  }

  async function loadSystem() {
    const { metrics } = await api.adminSystem();
    const fmt = (n) => n == null ? '—' : (n / 1024 / 1024 / 1024).toFixed(1) + ' GB';
    document.getElementById('admin-system').textContent = 'CPU ' + (metrics.cpu_percent == null ? '—' : metrics.cpu_percent + '%') +
      ' · RAM ' + fmt(metrics.memory_used) + ' / ' + fmt(metrics.memory_total) + ' · tiến trình ' + fmt(metrics.process_memory) +
      ' · ổ đĩa còn ' + fmt(metrics.disk_free) + ' / ' + fmt(metrics.disk_total);
  }

  async function loadForum() {
    const { messages } = await api.adminForumMessages();
    const host = document.getElementById('admin-forum');
    host.innerHTML = messages.length ? messages.map((m) => '<div class="version-row"><span><strong>@' + escapeHtml(m.username) + '</strong>: ' + escapeHtml(m.body) +
      ' · ' + escapeHtml(m.created_at) + '</span><button class="btn btn-ghost btn-sm" data-delete-message="' + m.id + '">Xoá tin</button></div>').join('') : '<p>Diễn đàn chưa có tin nhắn.</p>';
    host.querySelectorAll('[data-delete-message]').forEach((button) => button.addEventListener('click', async () => {
      if (!window.confirm('Xoá tin nhắn này khỏi diễn đàn?')) return;
      try { await api.adminDeleteForumMessage(button.dataset.deleteMessage); await loadForum(); say('Đã xoá tin nhắn.'); }
      catch (e) { say(e.message); }
    }));
  }

  async function loadTournaments() {
    const { tournaments } = await api.getTournaments();
    const host = document.getElementById('admin-tournaments');
    const details = await Promise.all(tournaments.map((t) => api.getTournament(t.id)));
    host.innerHTML = tournaments.length ? tournaments.map((t, i) => {
      const entries = details[i].tournament.entries.map((e) => '<span class="badge">#' + e.seed + ' ' + escapeHtml(e.name) + '</span>').join(' ');
      const standings = details[i].tournament.standings.map((s, rank) => '<div class="version-row">' + (rank+1) + '. ' + escapeHtml(s.name) + ' · ' + s.points + ' điểm · ' + s.wins + ' thắng / ' + s.draws + ' hoà</div>').join('');
      const games = details[i].tournament.games.map((g) => '<div class="version-row"><span>Vòng ' + g.round_number + ': ' +
        escapeHtml(g.team0_name || 'TBD') + ' vs ' + escapeHtml(g.team1_name || 'BYE') + ' · ' + escapeHtml(g.status) +
        (g.winner_name ? ' · Thắng: ' + escapeHtml(g.winner_name) : '') + '</span>' +
        (g.status === 'failed' ? '<button class="btn btn-ghost btn-sm" data-retry="' + escapeHtml(t.id) + '" data-game="' + escapeHtml(g.id) + '">Chạy lại</button>' : '') + '</div>').join('');
      const future = t.starts_at && new Date(t.starts_at).getTime() > Date.now();
      return '<div class="admin-card"><strong>' + escapeHtml(t.name) + '</strong> · ' + escapeHtml(t.status) + ' · ' + t.team_count + ' đội · ' + escapeHtml(t.format) + ' · ' + escapeHtml(t.map_id) +
        (t.starts_at ? ' · Bắt đầu: ' + escapeHtml(t.starts_at) : '') + (future ? ' · Tự mở theo lịch' : '') +
        (t.status === 'registration' && !future && !t.starts_at ? '<button class="btn btn-secondary btn-sm" data-start="' + escapeHtml(t.id) + '">Mở giải</button>' : '') +
        '<div class="version-row">Hạt giống: ' + (entries || 'Chưa bốc hạt giống') + '</div>' + standings + games + '</div>';
    }).join('') : '<p>Chưa có giải.</p>';
    host.querySelectorAll('[data-start]').forEach((button) => button.addEventListener('click', async () => {
      try { await api.startTournament(button.dataset.start); await loadTournaments(); say('Đã tạo bracket vòng đầu.'); }
      catch (error) { say(error.message); }
    }));
    host.querySelectorAll('[data-retry]').forEach((button) => button.addEventListener('click', async () => {
      try { await api.retryTournamentGame(button.dataset.retry, button.dataset.game); say('Đã đưa trận chạy lại vào hàng đợi.'); await loadTournaments(); }
      catch (error) { say(error.message); }
    }));
  }

  document.getElementById('tournament-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
      const startsAt = document.getElementById('tour-start').value;
      await api.createTournament({ name: document.getElementById('tour-name').value, description: document.getElementById('tour-description').value,
        format: document.getElementById('tour-format').value, map_id: document.getElementById('tour-map').value,
        starts_at: startsAt ? new Date(startsAt).toISOString() : null });
      event.target.reset(); say('Đã tạo giải đấu.'); await Promise.all([loadTournaments(), loadOverview()]);
    } catch (error) { say(error.message); }
  });

  try { await Promise.all([loadOverview(), loadUsers(), loadTournaments(), loadSubmissions(), loadSystem(), loadForum()]); setInterval(() => loadSystem().catch(() => {}), 10000); }
  catch (error) { say(error.message); }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
