// frontend/js/profile.js - 3-Tab Profile Interface Logic
import { api } from './api.js';
import { refreshUser, renderNavAuth } from './auth.js';

let currentUser = null;

/**
 * Điều hướng Tab (Tab Navigation Engine)
 */
function switchTab(tabKey) {
  const tabs = {
    stats: { btn: document.getElementById('tab-btn-stats'), panel: document.getElementById('tab-panel-stats') },
    history: { btn: document.getElementById('tab-btn-history'), panel: document.getElementById('tab-panel-history') },
    security: { btn: document.getElementById('tab-btn-security'), panel: document.getElementById('tab-panel-security') }
  };

  if (!tabs[tabKey]) tabKey = 'stats';

  Object.keys(tabs).forEach(key => {
    const item = tabs[key];
    if (key === tabKey) {
      item.btn?.classList.add('active');
      item.btn?.setAttribute('aria-selected', 'true');
      item.panel?.classList.add('active');
    } else {
      item.btn?.classList.remove('active');
      item.btn?.setAttribute('aria-selected', 'false');
      item.panel?.classList.remove('active');
    }
  });

  // Cập nhật hash trên URL mà không reload trang
  history.replaceState(null, null, `#${tabKey}`);

  if (tabKey === 'history') {
    loadHistoryData();
  }
}

/**
 * Tải thông tin hồ sơ và các chỉ số thống kê (Tab 1)
 */
async function loadProfileStats() {
  try {
    const res = await api.getUserProfile();
    if (!res || !res.success || !res.user) {
      throw new Error('Không thể tải dữ liệu hồ sơ.');
    }

    currentUser = res.user;
    const stats = currentUser.stats || {};

    // 1. Cập nhật Banner
    const dName = currentUser.display_name || currentUser.username;
    document.getElementById('header-display-name').textContent = dName;
    document.getElementById('header-username').textContent = currentUser.username;
    document.getElementById('header-role').textContent = currentUser.role === 'admin' ? 'Quản Trị Viên' : 'Thí Sinh ICPC';
    document.getElementById('header-badge').textContent = currentUser.badge || 'Tân Binh';
    document.getElementById('header-bio').textContent = currentUser.bio || 'Chưa có tiểu sử cá nhân.';

    const avatarInitial = (dName || '?').trim().slice(0, 1).toUpperCase();
    document.getElementById('header-avatar').textContent = avatarInitial;

    // 2. Cập nhật các khối thống kê (Stats Dashboard)
    document.getElementById('stat-elo').textContent = currentUser.rating || 1000;
    document.getElementById('stat-winrate').textContent = `${stats.win_rate || 0.0}%`;
    document.getElementById('stat-matches').textContent = stats.total_matches || 0;
    document.getElementById('stat-w').textContent = `${stats.wins || 0}W`;
    document.getElementById('stat-d').textContent = `${stats.draws || 0}D`;
    document.getElementById('stat-l').textContent = `${stats.losses || 0}L`;
    document.getElementById('stat-contests').textContent = stats.contests_count || 0;

    // 3. Điền vào Form Chỉnh Sửa
    document.getElementById('input-display-name').value = currentUser.display_name || currentUser.username;
    document.getElementById('select-avatar').value = currentUser.avatar_id || 'robot';
    document.getElementById('textarea-bio').value = currentUser.bio || '';

  } catch (err) {
    console.error('Lỗi tải profile:', err);
    document.getElementById('header-display-name').textContent = 'Chưa đăng nhập';
    document.getElementById('header-bio').textContent = 'Vui lòng đăng nhập để xem thông tin hồ sơ của bạn.';
  }
}

/**
 * Lưu thay đổi thông tin cá nhân
 */
async function handleProfileUpdate(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-save-profile');
  const msg = document.getElementById('profile-edit-msg');

  const displayName = document.getElementById('input-display-name').value.trim();
  const avatarId = document.getElementById('select-avatar').value;
  const bio = document.getElementById('textarea-bio').value.trim();

  btn.disabled = true;
  const oldText = btn.textContent;
  btn.textContent = '⏳ Đang lưu...';

  try {
    const res = await api.updateUserProfile({
      display_name: displayName,
      avatar_id: avatarId,
      bio: bio
    });

    if (res && res.success) {
      if (msg) {
        msg.textContent = '✅ Đã lưu cập nhật thông tin hồ sơ thành công!';
        msg.className = 'status-msg success';
      }
      await loadProfileStats();
    } else {
      throw new Error(res?.detail || 'Lỗi khi lưu.');
    }
  } catch (err) {
    if (msg) {
      msg.textContent = `Lỗi: ${err.message}`;
      msg.className = 'status-msg error';
    }
  } finally {
    btn.disabled = false;
    btn.textContent = oldText;
  }
}

/**
 * Tải Lịch sử Trận đấu và Contest (Tab 2)
 */
async function loadHistoryData() {
  const contestsTbody = document.getElementById('contests-history-body');
  const matchesTbody = document.getElementById('matches-history-body');

  try {
    const res = await api.getUserHistory();
    const contests = res.contests || [];
    const matches = res.matches || [];

    // Render Contests
    if (contestsTbody) {
      if (!contests.length) {
        contestsTbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Bạn chưa tham gia kỳ thi ICPC nào. Hãy vào trang Đấu trường để thử sức!</td></tr>';
      } else {
        contestsTbody.innerHTML = contests.map(c => `
          <tr>
            <td><strong>${escapeHtml(c.title)}</strong></td>
            <td>${escapeHtml(c.game_slug)}</td>
            <td><span class="rank-pill ${c.rank <= 3 && c.rank > 0 ? 'rank-' + c.rank : ''}">${c.rank || '-'}</span></td>
            <td><strong style="color: #38bdf8;">${c.points}</strong> pts</td>
            <td><span style="color:#4ade80;">${c.wins}W</span> / <span style="color:#facc15;">${c.draws}D</span> / <span style="color:#f43f5e;">${c.losses}L</span></td>
            <td>${c.passed_tests || '0/4'}</td>
          </tr>
        `).join('');
      }
    }

    // Render Matches
    if (matchesTbody) {
      if (!matches.length) {
        matchesTbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Chưa có trận đối kháng nào.</td></tr>';
      } else {
        matchesTbody.innerHTML = matches.map(m => {
          let badgeClass = 'badge-draw';
          let label = 'Hòa';
          if (m.result === 'win') { badgeClass = 'badge-win'; label = 'Thắng'; }
          else if (m.result === 'loss') { badgeClass = 'badge-loss'; label = 'Thua'; }

          return `
            <tr>
              <td>${escapeHtml(m.created_at || '')}</td>
              <td><strong>@${escapeHtml(m.opponent)}</strong></td>
              <td><span class="badge-result ${badgeClass}">${label}</span></td>
              <td><span style="font-family: monospace;">${escapeHtml(m.language || 'python')}</span></td>
              <td style="font-size: 0.82rem; color: var(--text-muted);">${escapeHtml(m.reason || '')}</td>
              <td>
                <a href="arena.html?replay=${encodeURIComponent(m.id)}" class="btn btn-ghost btn-sm" style="font-size: 0.75rem;">
                  ▶ Xem Replay
                </a>
              </td>
            </tr>
          `;
        }).join('');
      }
    }

  } catch (err) {
    console.error('Lỗi tải lịch sử:', err);
    if (contestsTbody) contestsTbody.innerHTML = `<tr><td colspan="6" style="color: var(--danger); text-align: center;">Lỗi tải dữ liệu giải đấu: ${err.message}</td></tr>`;
    if (matchesTbody) matchesTbody.innerHTML = `<tr><td colspan="6" style="color: var(--danger); text-align: center;">Lỗi tải lịch sử trận đấu: ${err.message}</td></tr>`;
  }
}

/**
 * Đo độ mạnh mật khẩu real-time (Tab 3)
 */
function checkPasswordStrength(password) {
  const meterFill = document.getElementById('meter-fill');
  const meterLabel = document.getElementById('meter-label');
  if (!meterFill || !meterLabel) return;

  if (!password) {
    meterFill.className = 'password-meter-fill';
    meterFill.style.width = '0%';
    meterLabel.textContent = 'Độ mạnh mật khẩu: Chưa nhập';
    return;
  }

  let score = 0;
  if (password.length >= 6) score++;
  if (password.length >= 10) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  if (score <= 2) {
    meterFill.className = 'password-meter-fill meter-weak';
    meterLabel.textContent = 'Độ mạnh mật khẩu: Yếu (Hãy thêm số hoặc ký tự đặc biệt)';
    meterLabel.style.color = '#f43f5e';
  } else if (score <= 4) {
    meterFill.className = 'password-meter-fill meter-medium';
    meterLabel.textContent = 'Độ mạnh mật khẩu: Trung bình';
    meterLabel.style.color = '#facc15';
  } else {
    meterFill.className = 'password-meter-fill meter-strong';
    meterLabel.textContent = 'Độ mạnh mật khẩu: Rất mạnh (An toàn cao)';
    meterLabel.style.color = '#4ade80';
  }
}

/**
 * Xử lý đổi mật khẩu (Tab 3)
 */
async function handlePasswordChange(e) {
  e.preventDefault();
  const currentPass = document.getElementById('current-password').value;
  const newPass = document.getElementById('new-password').value;
  const confirmPass = document.getElementById('confirm-password').value;
  const msg = document.getElementById('password-status-msg');
  const btn = document.getElementById('btn-submit-pwd');

  if (newPass !== confirmPass) {
    if (msg) {
      msg.textContent = 'Mật khẩu xác nhận không trùng khớp với mật khẩu mới.';
      msg.className = 'status-msg error';
    }
    return;
  }

  if (newPass.length < 6) {
    if (msg) {
      msg.textContent = 'Mật khẩu mới phải có ít nhất 6 ký tự.';
      msg.className = 'status-msg error';
    }
    return;
  }

  btn.disabled = true;
  const oldText = btn.textContent;
  btn.textContent = '⏳ Đang xử lý...';

  try {
    const res = await api.changePassword(currentPass, newPass);
    if (res && res.success) {
      if (msg) {
        msg.textContent = '🎉 ' + (res.message || 'Đổi mật khẩu thành công!');
        msg.className = 'status-msg success';
      }
      document.getElementById('current-password').value = '';
      document.getElementById('new-password').value = '';
      document.getElementById('confirm-password').value = '';
      checkPasswordStrength('');
    } else {
      throw new Error(res?.detail || 'Đổi mật khẩu thất bại.');
    }
  } catch (err) {
    if (msg) {
      msg.textContent = `Lỗi: ${err.message}`;
      msg.className = 'status-msg error';
    }
  } finally {
    btn.disabled = false;
    btn.textContent = oldText;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

document.addEventListener('DOMContentLoaded', async () => {
  const signedInUser = await refreshUser();
  renderNavAuth(signedInUser);

  if (!signedInUser) {
    location.href = '/login.html?redirect=/profile.html';
    return;
  }

  // Khởi tạo tab theo URL Hash (#stats, #history, #security)
  const hash = (location.hash || '').replace('#', '');
  const initialTab = ['stats', 'history', 'security'].includes(hash) ? hash : 'stats';

  // Sự kiện chuyển Tab
  document.getElementById('tab-btn-stats')?.addEventListener('click', () => switchTab('stats'));
  document.getElementById('tab-btn-history')?.addEventListener('click', () => switchTab('history'));
  document.getElementById('tab-btn-security')?.addEventListener('click', () => switchTab('security'));

  switchTab(initialTab);
  await loadProfileStats();

  // Sự kiện form Tab 1 (Chỉnh sửa hồ sơ)
  document.getElementById('profile-edit-form')?.addEventListener('submit', handleProfileUpdate);

  // Sự kiện form Tab 3 (Đổi mật khẩu)
  const newPassInput = document.getElementById('new-password');
  newPassInput?.addEventListener('input', (e) => checkPasswordStrength(e.target.value));

  const confirmPassInput = document.getElementById('confirm-password');
  confirmPassInput?.addEventListener('input', () => {
    const matchMsg = document.getElementById('password-match-msg');
    if (!matchMsg) return;
    if (confirmPassInput.value && confirmPassInput.value !== newPassInput.value) {
      matchMsg.textContent = '❌ Mật khẩu xác nhận không khớp.';
      matchMsg.style.color = '#f43f5e';
    } else if (confirmPassInput.value && confirmPassInput.value === newPassInput.value) {
      matchMsg.textContent = '✓ Mật khẩu khớp.';
      matchMsg.style.color = '#4ade80';
    } else {
      matchMsg.textContent = '';
    }
  });

  document.getElementById('password-change-form')?.addEventListener('submit', handlePasswordChange);
});
