import { api } from './api.js';
import { refreshUser, renderNavAuth } from './auth.js';
document.addEventListener('DOMContentLoaded', async () => {
  const user = await refreshUser(); renderNavAuth(user);
  if (!user) { location.href = '/login.html?redirect=/missions.html'; return; }
  const status = document.getElementById('status');
  async function load() {
    const [data, historyData] = await Promise.all([api.dailyMissions(), api.pointsHistory()]);
    document.getElementById('points').textContent = 'Điểm thưởng: ' + data.points;
    const historyHost = document.getElementById('points-history');
    historyHost.innerHTML = historyData.history.length ? historyData.history.map((item) =>
      '<div class="version-row"><span>' + escapeHtml(item.mission_key) + ' · +' + Number(item.points) + ' điểm</span><small>' + escapeHtml(item.created_at) + '</small></div>'
    ).join('') : '<p>Chưa có điểm thưởng được ghi nhận.</p>';
    document.getElementById('missions').innerHTML = data.missions.map((m) => '<article class="mission"><strong>' + escapeHtml(m.title) + '</strong><p>Tiến độ: ' + m.progress + '/' + m.target + ' · Thưởng: +' + m.reward + ' điểm</p>' + (m.done ? '<span>Đã nhận thưởng ✓</span>' : m.key === 'check_in' ? '<button class="btn btn-primary" id="check-in">Điểm danh</button>' : '<span>Tiến độ tự cập nhật khi bạn hoạt động.</span>') + '</article>').join('');
    document.getElementById('check-in')?.addEventListener('click', async () => { try { const result = await api.checkIn(); status.textContent = result.already_done ? 'Bạn đã điểm danh hôm nay.' : 'Điểm danh thành công, nhận điểm thưởng!'; await load(); } catch (e) { status.textContent = e.message; } });
  }
  try { await load(); } catch (e) { status.textContent = e.message; }
});
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
