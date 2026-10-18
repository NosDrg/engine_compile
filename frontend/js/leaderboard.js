// frontend/js/leaderboard.js
import { api } from './api.js';

const PAGE_SIZE = 15;
let allPlayers  = [];
let filtered    = [];
let currentPage = 1;
let currentLang = 'all';
let searchQuery = '';

const langEmoji = { python: '🐍', cpp: '⚙️', java: '☕' };
const langBadge = { python: 'badge-blue', cpp: 'badge-red', java: 'badge-gold' };

function escHtml(str) {
  return String(str).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])
  );
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadLeaderboard();

  // Search
  document.getElementById('lb-search-input')?.addEventListener('input', e => {
    searchQuery = e.target.value.toLowerCase();
    currentPage = 1;
    applyFilters();
  });

  // Language filter tabs
  document.querySelectorAll('.filter-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentLang = btn.dataset.lang;
      currentPage = 1;
      applyFilters();
    });
  });
});

async function loadLeaderboard() {
  try {
    const res = await api.getLeaderboard();
    allPlayers = (res.leaderboard || []).map((p, i) => ({
      username: p.display_name || p.username,
      handle: p.username,
      language: p.language || 'python',
      elo: p.rating,
      wins: p.wins,
      losses: p.losses,
      draws: p.draws,
      trend: 'same',
      rank: i + 1,
    }));

    renderPodium(allPlayers.slice(0, 3));
    applyFilters();

  } catch (err) {
    document.getElementById('podium-section').innerHTML =
      '<p style="color:var(--text-muted);">Không thể tải dữ liệu.</p>';
  }
}

function applyFilters() {
  filtered = allPlayers.filter(p => {
    const matchLang = currentLang === 'all' || p.language === currentLang;
    const matchSearch = !searchQuery || p.username.toLowerCase().includes(searchQuery);
    return matchLang && matchSearch;
  });
  renderTable();
  renderPagination();
}

function renderPodium(top3) {
  const el = document.getElementById('podium-section');
  if (!el || top3.length === 0) {
    el && (el.innerHTML = '<p style="color:var(--text-muted);text-align:center;">Chưa có dữ liệu top 3.</p>');
    return;
  }

  const order = top3.length >= 2 ? [top3[1], top3[0], top3[2]].filter(Boolean) : top3;
  const rankClass = ['rank-2', 'rank-1', 'rank-3'];
  const crowns = ['🥈', '🥇', '🥉'];

  el.innerHTML = order.map((p, i) => {
    const totalGames = p.wins + p.losses + p.draws;
    const winrate = totalGames > 0 ? ((p.wins / totalGames) * 100).toFixed(0) : 0;
    return `
      <div class="podium-item ${rankClass[i]}">
        <div class="podium-avatar-wrap">
          ${i === 1 ? '<div class="podium-crown">👑</div>' : ''}
          <img class="podium-avatar" src="../assets/default_avatar.jpg" alt="${escHtml(p.username)}">
        </div>
        <a class="podium-name" href="profile.html?username=${encodeURIComponent(p.handle)}">${escHtml(p.username)}</a>
        <div class="podium-score">${p.elo} ELO</div>
        <div class="podium-lang mt-1">
          <span class="badge ${langBadge[p.language] || 'badge-purple'}">
            ${langEmoji[p.language] || '🤖'} ${p.language?.toUpperCase() || 'BOT'}
          </span>
        </div>
        <div class="podium-stand">${crowns[i]}</div>
      </div>
    `;
  }).join('');
}

function renderTable() {
  const tbody = document.getElementById('lb-tbody');
  if (!tbody) return;

  const start = (currentPage - 1) * PAGE_SIZE;
  const page  = filtered.slice(start, start + PAGE_SIZE);

  if (page.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);">
      ${searchQuery ? 'Không tìm thấy thí sinh nào.' : 'Chưa có dữ liệu.'}
    </td></tr>`;
    return;
  }

  const trendIcon = { up: '▲', down: '▼', same: '—' };
  const trendClass = { up: 'trend-up', down: 'trend-down', same: 'trend-same' };

  tbody.innerHTML = page.map(p => {
    const totalGames = p.wins + p.losses + p.draws;
    const winrate = totalGames > 0 ? ((p.wins / totalGames) * 100).toFixed(0) : 0;
    const rankLabel = p.rank <= 3
      ? ['🥇','🥈','🥉'][p.rank - 1]
      : `<span class="rank-num">${p.rank}</span>`;

    return `
      <tr>
        <td class="rank-cell">${rankLabel}</td>
        <td>
          <div class="player-cell">
            <img class="player-avatar" src="assets/default_avatar.jpg" alt="${escHtml(p.username)}">
            <div class="player-info">
              <a class="player-name" href="profile.html?username=${encodeURIComponent(p.handle)}">${escHtml(p.username)}</a>
              <div class="player-sub">${totalGames} trận</div>
            </div>
          </div>
        </td>
        <td>
          <span class="badge ${langBadge[p.language] || 'badge-purple'}">
            ${langEmoji[p.language] || '🤖'} ${(p.language || 'bot').toUpperCase()}
          </span>
        </td>
        <td class="score-cell">${p.elo}</td>
        <td>
          <span style="color:var(--success);">${p.wins}W</span>
          <span style="color:var(--text-faint);margin:0 4px;">/</span>
          <span style="color:var(--danger);">${p.losses}L</span>
          <span style="color:var(--text-faint);margin:0 4px;">/</span>
          <span style="color:var(--text-muted);">${p.draws}D</span>
        </td>
        <td class="winrate-bar-cell">
          <div class="winrate-bar-wrap">
            <div class="winrate-bar">
              <div class="winrate-fill" style="width:${winrate}%"></div>
            </div>
            <span class="winrate-pct">${winrate}%</span>
          </div>
        </td>
        <td>
          <span class="${trendClass[p.trend] || 'trend-same'}" style="font-size:0.8rem;font-weight:700;">
            ${trendIcon[p.trend] || '—'}
          </span>
        </td>
      </tr>
    `;
  }).join('');
}

function renderPagination() {
  const el = document.getElementById('lb-pagination');
  if (!el) return;

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  if (totalPages <= 1) { el.innerHTML = ''; return; }

  let html = `<button class="page-btn" id="pg-prev" ${currentPage === 1 ? 'disabled' : ''}>‹</button>`;
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
      html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    } else if (i === currentPage - 2 || i === currentPage + 2) {
      html += `<span style="color:var(--text-faint);padding:0 4px;">…</span>`;
    }
  }
  html += `<button class="page-btn" id="pg-next" ${currentPage === totalPages ? 'disabled' : ''}>›</button>`;
  el.innerHTML = html;

  el.querySelectorAll('[data-page]').forEach(btn => {
    btn.addEventListener('click', () => {
      currentPage = parseInt(btn.dataset.page);
      applyFilters();
      window.scrollTo({ top: 300, behavior: 'smooth' });
    });
  });
  el.querySelector('#pg-prev')?.addEventListener('click', () => {
    if (currentPage > 1) { currentPage--; applyFilters(); }
  });
  el.querySelector('#pg-next')?.addEventListener('click', () => {
    if (currentPage < totalPages) { currentPage++; applyFilters(); }
  });
}
