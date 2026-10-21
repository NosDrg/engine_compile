// frontend/js/home.js
import { api } from './api.js';
import { demoLeaderboard } from './demo-data.js';

document.addEventListener('DOMContentLoaded', async () => {
  // ── Animated counters ─────────────────────────────────────────
  function animateCount(el, target, suffix = '') {
    let current = 0;
    const step = Math.max(1, Math.floor(target / 40));
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current.toLocaleString('vi-VN') + suffix;
      if (current >= target) clearInterval(timer);
    }, 30);
  }

  // Load opponents list to get player count
  try {
    const res = await api.getStats();
    const statPlayers = document.getElementById('stat-players');
    const statMatches = document.getElementById('stat-matches');
    if (statPlayers) animateCount(statPlayers, res.stats.players);
    if (statMatches) animateCount(statMatches, res.stats.matches);
  } catch (_) {
    const statPlayers = document.getElementById('stat-players');
    const statMatches = document.getElementById('stat-matches');
    if (statPlayers) statPlayers.textContent = '—';
    if (statMatches) statMatches.textContent = '—';
  }

  // ── Leaderboard preview ───────────────────────────────────────
  const lbList = document.getElementById('lb-preview-list');
  if (lbList) {
    try {
      const res = await api.getLeaderboard();
      let opponents = res.leaderboard || [];

      if (opponents.length === 0) {
        opponents = demoLeaderboard;
        const notice = document.getElementById('home-demo-notice');
        if (notice) notice.hidden = false;
      }

      const sorted = opponents.slice(0, 5).map((p) => ({ ...p, elo: p.rating }));

      lbList.innerHTML = sorted.map((p, i) => `
        <div class="lb-row">
          <div class="lb-rank ${i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : ''}">
            ${i + 1}
          </div>
          <img class="lb-avatar" src="assets/default_avatar.jpg" alt="${escHtml(p.username)}">
          <div class="lb-name">${escHtml(p.username)}</div>
          <div class="lb-lang"><span class="badge badge-purple">${(p.language || 'bot').toUpperCase()}</span></div>
          <div class="lb-score">${p.elo} ELO</div>
        </div>
      `).join('');

    } catch (err) {
      lbList.innerHTML = '<p class="home-empty-state">Không thể tải leaderboard.</p>';
    }
  }
});

function escHtml(str) {
  return String(str).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])
  );
}
