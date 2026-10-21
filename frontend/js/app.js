import { BoardView } from './board.js';
import { MatchController } from './match.js';
import { api } from './api.js';
import { refreshUser } from './auth.js';

document.addEventListener('DOMContentLoaded', async () => {
  const user = await refreshUser();
  if (!user) { location.href = '/login.html?redirect=/arena.html'; return; }

  const username = document.getElementById('my-bot-id');
  const code = document.getElementById('my-bot-code');
  const language = document.getElementById('my-bot-lang');
  const status = document.getElementById('my-bot-status');
  const opponents = document.getElementById('select-opponent');
  username.value = user.username;
  username.readOnly = true;

  const controller = new MatchController(new BoardView('board-container'));
  window.matchController = controller;
  document.getElementById('btn-cancel-match')?.addEventListener('click', async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      const cancelled = await controller.cancelWaitingMatch();
      showStatus(cancelled ? 'Đã hủy trận đang chờ.' : 'Trận không còn ở trạng thái chờ.', !cancelled);
    } catch (error) { showStatus(error.message, true); }
    finally { button.disabled = false; }
  });
  document.getElementById('replay-toggle')?.addEventListener('click', () => {
    controller.paused = !controller.paused;
    controller.updateReplayControls();
  });
  document.getElementById('replay-reset')?.addEventListener('click', () => {
    controller.paused = true;
    controller.renderReplayStep(0);
  });
  document.getElementById('replay-seek')?.addEventListener('input', (event) => {
    controller.paused = true;
    controller.renderReplayStep(Number(event.target.value));
  });
  document.getElementById('replay-speed')?.addEventListener('change', (event) => {
    controller.playbackSpeed = Number(event.target.value) || 1;
    controller.startTimer();
  });
  const safe = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  async function loadOpponents() {
    opponents.innerHTML = '<option value="">Đang tải...</option>';
    try {
      const res = await api.getOpponents(user.username);
      opponents.innerHTML = '';
      if (!res.opponents.length) opponents.innerHTML = '<option value="">Chưa có bot hợp lệ nào khác</option>';
      res.opponents.forEach((item) => {
        const option = document.createElement('option');
        option.value = item.username;
        option.textContent = item.username + ' (' + item.language.toUpperCase() + ')';
        opponents.appendChild(option);
      });
    } catch (error) { opponents.innerHTML = '<option value="">Không tải được đối thủ</option>'; }
  }

  async function loadSubmissions() {
    const host = document.getElementById('submission-history');
    if (!host) return;
    try {
      const res = await api.getSubmissions();
      host.innerHTML = res.submissions.length ? res.submissions.map((item) =>
        '<div class="version-row"><span><strong>' + safe(item.version_name) + '</strong> · ' + safe(item.language) +
        ' · ' + safe(item.status) + (item.is_active ? ' · <b>Đang hoạt động</b>' : '') + '</span>' +
        (!item.is_active && item.status === 'VALID' ? '<button class="btn btn-ghost btn-sm" data-activate="' + safe(item.id) + '">Dùng phiên bản này</button>' : '') +
        '</div>' + (item.error_log ? '<pre class="submission-error">' + safe(item.error_log.slice(0, 1200)) + '</pre>' : '')
      ).join('') : '<p>Chưa có phiên bản bot.</p>';
      host.querySelectorAll('[data-activate]').forEach((button) => button.addEventListener('click', async () => {
        try { await api.activateSubmission(button.dataset.activate); await loadSubmissions(); }
        catch (error) { showStatus(error.message, true); }
      }));
    } catch (error) { host.textContent = error.message; }
  }

  function showStatus(message, failed = false) {
    status.textContent = message;
    status.className = 'status-msg ' + (failed ? 'error' : 'success');
  }

  document.getElementById('btn-refresh-opponents')?.addEventListener('click', loadOpponents);
  document.getElementById('btn-validate-my-bot')?.addEventListener('click', async (event) => {
    const button = event.currentTarget;
    if (!code.value.trim()) return showStatus('Nhập code trước khi kiểm tra.', true);
    button.disabled = true; showStatus('Đang kiểm tra…');
    try {
      const result = await api.validateCode(code.value, language.value);
      showStatus(result.success ? 'Code hợp lệ.' : (result.error || 'Code chưa hợp lệ.'), !result.success);
    } catch (error) { showStatus(error.message, true); }
    finally { button.disabled = false; }
  });
  document.getElementById('btn-submit-my-bot')?.addEventListener('click', async (event) => {
    const button = event.currentTarget;
    if (!code.value.trim()) return showStatus('Nhập code trước khi nộp.', true);
    button.disabled = true; showStatus('Đang biên dịch và lưu phiên bản…');
    try {
      const versionName = document.getElementById('version-name')?.value.trim() || 'Submission';
      const result = await api.submitCode(code.value, language.value, versionName);
      if (!result.success) { showStatus(result.error || 'Biên dịch thất bại.', true); }
      else {
        const versions = await api.getSubmissions();
        if (!versions.submissions.some((v) => v.is_active)) await api.activateSubmission(result.submission_id);
        showStatus('Đã lưu phiên bản ' + versionName + '.');
        await Promise.all([loadSubmissions(), loadOpponents()]);
      }
    } catch (error) { showStatus(error.message, true); }
    finally { button.disabled = false; }
  });
  document.getElementById('btn-start-match')?.addEventListener('click', async (event) => {
    const rival = opponents.value;
    if (!rival) return showStatus('Chọn đối thủ trước khi đấu.', true);
    const button = event.currentTarget; button.disabled = true;
    const seedText = document.getElementById('match-seed')?.value.trim();
    const seed = seedText === '' ? null : Number(seedText);
    if (seed !== null && (!Number.isSafeInteger(seed) || seed < 0)) { button.disabled = false; return showStatus('Seed phải là số nguyên không âm trong phạm vi trình duyệt hỗ trợ.', true); }
    try { await controller.start({ sub_id: user.username, ranked: document.getElementById('match-mode')?.value === 'ranked', seed,
      map_id: document.getElementById('match-map')?.value || 'classic' }, { sub_id: rival }); }
    catch (error) { showStatus(error.message, true); }
    finally { button.disabled = false; }
  });
  document.getElementById('btn-rematch')?.addEventListener('click', () => {
    if (opponents.value) controller.start({ sub_id: user.username, ranked: document.getElementById('match-mode')?.value === 'ranked' }, { sub_id: opponents.value });
  });

  document.getElementById('btn-create-team')?.addEventListener('click', async () => {
    try {
      const result = await api.createTeam(document.getElementById('team-name').value);
      document.getElementById('team-status').textContent = 'Đội đã tạo. Mã mời: ' + result.join_code;
      await loadTeam();
    } catch (error) { document.getElementById('team-status').textContent = error.message; }
  });
  document.getElementById('btn-join-team')?.addEventListener('click', async () => {
    try {
      await api.joinTeam(document.getElementById('team-code').value);
      document.getElementById('team-status').textContent = 'Đã tham gia đội.';
      await loadTeam();
    } catch (error) { document.getElementById('team-status').textContent = error.message; }
  });

  async function loadTeam() {
    const host = document.getElementById('team-status');
    try {
      const result = await api.getTeam();
      const manage = document.getElementById('team-manage');
      if (manage) manage.hidden = !result.team;
      if (result.team) {
        host.textContent = result.team.name + ' · ' + result.team.members.map(m => m.username + ' (' + m.role + ')').join(', ') +
          (result.team.member_role === 'owner' ? ' · Mã mời: ' + result.team.join_code : '');
        const controls = document.getElementById('team-members');
        const canManage = ['owner','captain'].includes(result.team.member_role);
        if (controls) controls.innerHTML = result.team.members.map((member) => {
          const isSelf = member.id === user.id, canRemove = canManage && !isSelf && member.role !== 'owner' && (result.team.member_role === 'owner' || member.role === 'member');
          const roleControl = result.team.member_role === 'owner' && !isSelf && member.role !== 'owner' ?
            '<button class="btn btn-ghost btn-sm" data-member-role="' + member.id + '" data-next-role="' + (member.role === 'captain' ? 'member' : 'captain') + '">' + (member.role === 'captain' ? 'Hạ đội trưởng' : 'Đặt đội trưởng') + '</button>' : '';
          const contestantControl = canManage ? (member.id === result.team.contestant_id ?
            '<span class="badge">Bot đại diện giải</span>' : '<button class="btn btn-ghost btn-sm" data-contestant="' + member.id + '">Chọn bot đại diện</button>') : '';
          const removeControl = canRemove ? '<button class="btn btn-ghost btn-sm" data-remove-member="' + member.id + '">Xoá</button>' : '';
          return '<div class="version-row"><span>' + safe(member.display_name || member.username) + ' · ' + safe(member.role) + '</span>' + contestantControl + roleControl + removeControl + '</div>';
        }).join('');
        controls?.querySelectorAll('[data-member-role]').forEach(button => button.addEventListener('click', async () => {
          try { await api.setTeamMemberRole(button.dataset.memberRole, button.dataset.nextRole); await loadTeam(); }
          catch (error) { host.textContent = error.message; }
        }));
        controls?.querySelectorAll('[data-contestant]').forEach(button => button.addEventListener('click', async () => {
          try { await api.setTeamContestant(button.dataset.contestant); await loadTeam(); }
          catch (error) { host.textContent = error.message; }
        }));
        controls?.querySelectorAll('[data-remove-member]').forEach(button => button.addEventListener('click', async () => {
          if (!window.confirm('Xoá thành viên này khỏi đội?')) return;
          try { await api.removeTeamMember(button.dataset.removeMember); await loadTeam(); }
          catch (error) { host.textContent = error.message; }
        }));
        const rotate = document.getElementById('btn-rotate-team-code');
        if (rotate) rotate.hidden = !canManage;
      } else host.textContent = 'Bạn chưa thuộc đội nào.';
    } catch (error) { host.textContent = error.message; }
  }

  document.getElementById('btn-leave-team')?.addEventListener('click', async () => {
    try { await api.leaveTeam(); document.getElementById('team-status').textContent = 'Đã rời đội.'; await loadTeam(); }
    catch (error) { document.getElementById('team-status').textContent = error.message; }
  });
  document.getElementById('btn-rotate-team-code')?.addEventListener('click', async () => {
    try { const result = await api.rotateTeamCode(); document.getElementById('team-status').textContent = 'Mã mời mới: ' + result.join_code; }
    catch (error) { document.getElementById('team-status').textContent = error.message; }
  });

  async function loadTournaments() {
    const host = document.getElementById('tournament-list');
    if (!host) return;
    try {
      const result = await api.getTournaments();
      const details = await Promise.all(result.tournaments.map(t => api.getTournament(t.id)));
      host.innerHTML = result.tournaments.length ? result.tournaments.map((t, index) => {
        const games = details[index].tournament.games.map(g => '<div class="version-row">Vòng ' + g.round_number + ': ' +
          safe(g.team0_name || 'TBD') + ' vs ' + safe(g.team1_name || 'BYE') + ' · ' + safe(g.status) +
          (g.winner_name ? ' · Thắng: ' + safe(g.winner_name) : '') + '</div>').join('');
        const standings = details[index].tournament.standings.map((s, rank) => '<div class="version-row">' + (rank+1) + '. ' + safe(s.name) + ' · ' + s.points + 'đ · ' + s.wins + ' thắng / ' + s.draws + ' hoà</div>').join('');
        return '<div class="tournament-card"><div class="version-row"><span><strong>' + safe(t.name) + '</strong> · ' + safe(t.status) + ' · ' + t.team_count + ' đội · ' + safe(t.format) + ' · ' + safe(t.map_id) + (t.starts_at ? ' · ' + safe(t.starts_at) : '') + '</span>' +
          (t.status === 'registration' ? '<button class="btn btn-ghost btn-sm" data-join-tour="' + safe(t.id) + '">Đăng ký đội</button>' : '') +
          '</div>' + (standings ? '<h3>Bảng điểm</h3>' + standings : '') + games + '</div>';
      }).join('') : '<p>Chưa có giải đấu.</p>';
      host.querySelectorAll('[data-join-tour]').forEach(button => button.addEventListener('click', async () => {
        try { await api.joinTournament(button.dataset.joinTour); await loadTournaments(); }
        catch (error) { host.textContent = error.message; }
      }));
    } catch (error) { host.textContent = error.message; }
  }

  async function loadRecentMatches() {
    const host = document.getElementById('recent-matches');
    if (!host) return;
    try {
      const result = await api.getMatches();
      host.innerHTML = result.matches.length ? result.matches.map(m =>
        '<div class="version-row"><button class="btn btn-ghost btn-sm" data-replay="' + safe(m.id) + '">' +
        safe(m.user0_name) + ' vs ' + safe(m.user1_name) + '</button><span>' + safe(m.reason) + ' · ' + safe(m.created_at) + '</span></div>'
      ).join('') : '<p>Chưa có trận đã lưu.</p>';
      host.querySelectorAll('[data-replay]').forEach(button => button.addEventListener('click', async () => {
        try { controller.playReplay(await api.getMatchState(button.dataset.replay)); }
        catch (error) { showStatus(error.message, true); }
      }));
    } catch (error) { host.textContent = error.message; }
  }

  await Promise.all([loadOpponents(), loadSubmissions(), loadTeam(), loadTournaments(), loadRecentMatches()]);
});
