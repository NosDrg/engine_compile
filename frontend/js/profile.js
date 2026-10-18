import { api } from './api.js';
import { refreshUser, renderNavAuth } from './auth.js';

const $ = (id) => document.getElementById(id);

document.addEventListener('DOMContentLoaded', async () => {
  const username = new URLSearchParams(location.search).get('username');
  const status = $('status');
  const signedInUser = await refreshUser();
  renderNavAuth(signedInUser);

  if (username) {
    await loadPublicProfile(username, status);
    return;
  }
  if (!signedInUser) { location.href = '/login.html?redirect=/profile.html'; return; }

  try {
    const [{ user }, { events }] = await Promise.all([api.me(), api.ratingHistory()]);
    renderSummary(user);
    $('display-name').value = user.display_name || user.username;
    $('avatar-id').value = user.avatar_id || 'robot';
    $('bio').value = user.bio || '';
    $('profile-public').checked = user.profile_public !== false && user.profile_public !== 0;
    $('profile-url').innerHTML = profileLink(user);
    $('history').innerHTML = events.length ? events.map((event) =>
      '<article class="match-row"><span>Rating ' + event.old_rating + ' → ' + event.new_rating + '</span><span>' + (event.new_rating >= event.old_rating ? '+' : '') + (event.new_rating - event.old_rating) + ' · ' + escapeHtml(event.created_at) + '</span></article>'
    ).join('') : '<p>Chưa có trận xếp hạng.</p>';
  } catch (error) { status.textContent = error.message; }

  $('profile-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const { user } = await api.updateProfile({
        display_name: $('display-name').value.trim(),
        avatar_id: $('avatar-id').value,
        bio: $('bio').value.trim(),
        profile_public: $('profile-public').checked,
      });
      renderSummary(user);
      $('profile-url').innerHTML = profileLink(user);
      status.textContent = 'Đã lưu hồ sơ.';
      renderNavAuth(user);
    } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; }
  });

  $('password-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const current = $('current-password');
    const next = $('new-password');
    const confirm = $('confirm-password');
    if (next.value !== confirm.value) { status.textContent = 'Mật khẩu nhập lại không khớp.'; return; }
    const button = event.currentTarget.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      await api.changePassword(current.value, next.value);
      current.value = next.value = confirm.value = '';
      status.textContent = 'Đã đổi mật khẩu. Các phiên đăng nhập khác đã bị đăng xuất.';
    } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; }
  });
});

async function loadPublicProfile(username, status) {
  $('page-title').textContent = 'Hồ sơ người chơi';
  $('edit-section').hidden = true;
  $('history-section').hidden = true;
  $('password-section').hidden = true;
  try {
    const { profile } = await api.publicProfile(username);
    document.title = (profile.display_name || profile.username) + ' · Bot Arena';
    renderSummary(profile);
    $('matches-section').hidden = false;
    $('matches').innerHTML = profile.match_history.length ? profile.match_history.map((match) => {
      const label = match.result === 'win' ? 'Thắng' : match.result === 'loss' ? 'Thua' : 'Hòa';
      return '<article class="match-row"><span>' + label + ' với @' + escapeHtml(match.opponent) + (match.ranked ? ' · Xếp hạng' : ' · Giao hữu') + '</span><span>' + escapeHtml(match.created_at) + '</span></article>';
    }).join('') : '<p>Chưa có trận đấu được hiển thị.</p>';
  } catch (error) {
    $('summary').textContent = error.message;
    status.textContent = 'Hồ sơ không tồn tại hoặc đang được đặt ở chế độ riêng tư.';
  }
}

function renderSummary(user) {
  const avatar = ({ robot: '🤖', rock: '🪨', paper: '📄', scissors: '✂️', trophy: '🏆' })[user.avatar_id] || escapeHtml((user.display_name || user.username || '?').trim().slice(0, 1).toUpperCase());
  $('summary').innerHTML = '<div class="profile-heading"><div class="profile-avatar" aria-hidden="true">' + avatar + '</div><div><h2>' + escapeHtml(user.display_name || user.username) + '</h2><p>@' + escapeHtml(user.username) + '</p></div></div>' +
    (user.bio ? '<p style="margin-top:14px">' + escapeHtml(user.bio) + '</p>' : '') +
    '<div class="profile-stats"><span><strong>' + Number(user.rating || 1000) + '</strong>Rating</span><span><strong>' + Number(user.wins || 0) + '</strong>Thắng</span><span><strong>' + Number(user.losses || 0) + '</strong>Thua</span><span><strong>' + Number(user.draws || 0) + '</strong>Hòa</span></div><a href="/missions.html">Xem điểm thưởng và nhiệm vụ</a>';
}

function profileLink(user) {
  if (!user.profile_public) return 'Hồ sơ đang ở chế độ riêng tư.';
  const path = '/profile.html?username=' + encodeURIComponent(user.username);
  return 'Liên kết công khai: <a class="profile-link" href="' + escapeHtml(path) + '">' + escapeHtml(location.origin + path) + '</a>';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
}
