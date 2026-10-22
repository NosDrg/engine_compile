// frontend/js/arena.js - ICPC Contest-Driven Arena Logic
import { api } from './api.js';

let currentContest = null;
let countdownInterval = null;
let remainingSeconds = 0;
let isEditorLocked = false;

// Anti-Cheat Proctor Variables
let blurCount = 0;
let totalBlurSec = 0;
let blurStartTime = null;

// Auto-save Variables
let localSaveTimeout = null;
let serverSaveInterval = null;
let lastSyncedCode = '';

// Replay state
let currentReplay = null;
let replayStep = 0;
let replayTimer = null;
let isPlaying = false;

/**
 * Khởi tạo đồng hồ đếm ngược ICPC Contest
 */
function initCountdown(seconds, status) {
  remainingSeconds = Math.max(0, parseInt(seconds || 0, 10));
  const countdownEl = document.getElementById('contest-countdown');
  const statusEl = document.getElementById('contest-status');

  if (countdownInterval) clearInterval(countdownInterval);

  function updateDisplay() {
    if (!countdownEl) return;
    const hrs = String(Math.floor(remainingSeconds / 3600)).padStart(2, '0');
    const mins = String(Math.floor((remainingSeconds % 3600) / 60)).padStart(2, '0');
    const secs = String(remainingSeconds % 60).padStart(2, '0');
    countdownEl.textContent = `${hrs}:${mins}:${secs}`;

    // Báo động đỏ khi dưới 5 phút
    if (remainingSeconds <= 300 && remainingSeconds > 0) {
      countdownEl.classList.add('urgent');
    } else {
      countdownEl.classList.remove('urgent');
    }

    if (statusEl) {
      statusEl.textContent = status || (remainingSeconds > 0 ? 'RUNNING' : 'FINISHED');
      statusEl.className = 'badge-status ' + (remainingSeconds > 0 ? 'badge-running' : 'badge-finished');
    }
  }

  updateDisplay();

  if (remainingSeconds <= 0) {
    lockEditorForContestEnd();
    return;
  }

  countdownInterval = setInterval(() => {
    remainingSeconds--;
    if (remainingSeconds <= 0) {
      clearInterval(countdownInterval);
      updateDisplay();
      handleContestTimeUp();
    } else {
      updateDisplay();
    }
  }, 1000);
}

/**
 * Xử lý khi hết giờ làm bài (Time's Up)
 */
async function handleContestTimeUp() {
  lockEditorForContestEnd();
  const statusEl = document.getElementById('my-bot-status');
  if (statusEl) {
    statusEl.textContent = '⏳ Hết giờ làm bài! Hệ thống đang tự động khóa editor và nộp bài dự thi...';
    statusEl.className = 'status-msg warning';
  }

  try {
    if (currentContest) {
      const codeEl = document.getElementById('my-bot-code');
      const langEl = document.getElementById('my-bot-lang');
      const sourceCode = codeEl?.value || '';
      const language = langEl?.value || 'python';

      // 1. Tự động nộp bài cuối cùng (Auto-submit)
      await api.submitContestBot(currentContest.id, { source_code: sourceCode, language: language });

      if (statusEl) {
        statusEl.textContent = '✅ Đã hoàn tất Auto-Submit! Đang tiến hành vòng đối đầu Round-Robin...';
        statusEl.className = 'status-msg success';
      }

      // 2. Kích hoạt tính điểm và vòng đấu chéo
      await api.triggerContestEvaluate(currentContest.id);

      // 3. Tự động chuyển qua tab Leaderboard và tải dữ liệu mới nhất
      switchRightTab('leaderboard');
      await loadContestLeaderboard(currentContest.id);
    }
  } catch (err) {
    console.error('Lỗi khi auto-submit:', err);
    if (statusEl) {
      statusEl.textContent = `Thông báo: Cuộc thi đã kết thúc. (${err.message})`;
      statusEl.className = 'status-msg';
    }
  }
}

/**
 * Khóa toàn bộ Editor khi hết giờ
 */
function lockEditorForContestEnd() {
  isEditorLocked = true;
  const codeEl = document.getElementById('my-bot-code');
  const btnRun = document.getElementById('btn-run-tests');
  const btnSub = document.getElementById('btn-contest-submit');
  const autosave = document.getElementById('autosave-text');

  if (codeEl) codeEl.readOnly = true;
  if (btnRun) btnRun.disabled = true;
  if (btnSub) btnSub.disabled = true;
  if (autosave) autosave.textContent = 'Đã khóa bài thi (Hết giờ)';
}

/**
 * Trình Chống Gian Lận (Anti-Cheat Proctor)
 */
function initAntiCheatProctor() {
  const warningEl = document.getElementById('focus-warning');

  function triggerBlur() {
    blurStartTime = Date.now();
  }

  function triggerFocus() {
    if (blurStartTime) {
      const elapsed = Math.round((Date.now() - blurStartTime) / 1000);
      totalBlurSec += Math.max(1, elapsed);
      blurCount++;
      blurStartTime = null;
      updateWarningUI();
    }
  }

  function updateWarningUI() {
    if (!warningEl) return;
    if (blurCount > 0) {
      warningEl.classList.add('active');
      warningEl.innerHTML = `⚠️ Cảnh báo: Rời tab <strong>${blurCount}</strong> lần (<strong>${totalBlurSec}</strong>s)`;
      if (blurCount >= 3) {
        warningEl.classList.add('danger');
      }
    }
  }

  window.addEventListener('blur', triggerBlur);
  window.addEventListener('focus', triggerFocus);

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      triggerBlur();
    } else {
      triggerFocus();
    }
  });
}

/**
 * Cơ chế Auto-Save 2 tầng
 */
function initAutoSave() {
  const codeEl = document.getElementById('my-bot-code');
  const autosaveText = document.getElementById('autosave-text');
  const autosaveTag = document.getElementById('autosave-indicator');
  if (!codeEl) return;

  // Tầng 1: Lưu vào LocalStorage mỗi khi gõ phím (debounce 500ms)
  codeEl.addEventListener('input', () => {
    if (isEditorLocked) return;
    if (autosaveTag) autosaveTag.className = 'autosave-tag saving';
    if (autosaveText) autosaveText.textContent = 'Đang lưu nháp...';

    clearTimeout(localSaveTimeout);
    localSaveTimeout = setTimeout(() => {
      if (currentContest) {
        localStorage.setItem(`icpc_draft_${currentContest.id}`, codeEl.value);
        if (autosaveTag) autosaveTag.className = 'autosave-tag saved';
        if (autosaveText) autosaveText.textContent = 'Đã lưu vào máy';
      }
    }, 500);
  });

  // Tầng 2: Định kỳ 30 giây gửi draft ngầm lên Server nếu có thay đổi
  serverSaveInterval = setInterval(async () => {
    if (isEditorLocked || !currentContest) return;
    const currentCode = codeEl.value.trim();
    if (currentCode && currentCode !== lastSyncedCode) {
      try {
        const langEl = document.getElementById('my-bot-lang');
        const lang = langEl?.value || 'python';
        await api.runTestSuite(currentContest.id, {
          source_code: currentCode,
          language: lang,
          blur_count: blurCount,
          total_blur_sec: totalBlurSec
        });
        lastSyncedCode = currentCode;
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0];
        if (autosaveTag) autosaveTag.className = 'autosave-tag saved';
        if (autosaveText) autosaveText.textContent = `Đã lưu máy chủ (${timeStr})`;
      } catch (e) {
        // Lỗi ngầm không làm phiền thí sinh
      }
    }
  }, 30000);
}

/**
 * Chạy Bộ Test Case Nhân Tạo
 */
async function runTestSuiteAction() {
  if (isEditorLocked || !currentContest) return;

  const codeEl = document.getElementById('my-bot-code');
  const langEl = document.getElementById('my-bot-lang');
  const statusEl = document.getElementById('my-bot-status');
  const btnRun = document.getElementById('btn-run-tests');
  const summaryBox = document.getElementById('test-summary-box');
  const listContainer = document.getElementById('test-cases-list');

  const sourceCode = codeEl?.value || '';
  const language = langEl?.value || 'python';

  if (!sourceCode.trim()) {
    if (statusEl) {
      statusEl.textContent = 'Vui lòng nhập mã nguồn thuật toán trước khi kiểm thử.';
      statusEl.className = 'status-msg error';
    }
    return;
  }

  btnRun.disabled = true;
  const originalText = btnRun.textContent;
  btnRun.textContent = '⏳ Đang kiểm thử sandbox...';
  if (statusEl) {
    statusEl.textContent = 'Đang thực thi các test case trong sandbox bảo mật...';
    statusEl.className = 'status-msg';
  }

  try {
    const res = await api.runTestSuite(currentContest.id, {
      source_code: sourceCode,
      language: language,
      blur_count: blurCount,
      total_blur_sec: totalBlurSec
    });

    lastSyncedCode = sourceCode;

    if (summaryBox) {
      const isAllPass = res.passed === res.total && res.total > 0;
      summaryBox.innerHTML = `
        <div>
          Trạng thái: <span class="test-badge-score ${isAllPass ? 'all-pass' : 'has-fail'}">${res.passed}/${res.total} Test Cases PASS</span>
        </div>
        <div>
          Tốc độ phản xạ TB: <strong>${res.avg_time_ms} ms</strong>
        </div>
      `;
    }

    if (listContainer && res.details) {
      listContainer.innerHTML = res.details.map(d => {
        const statusClass = (d.status || '').toLowerCase();
        return `
          <div class="test-case-row">
            <div>
              <div class="test-case-name">${escapeHtml(d.name)}</div>
              <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">${escapeHtml(d.message || '')}</div>
            </div>
            <div class="tc-metrics">
              <span>⏱ ${d.time_ms}ms</span>
              <span class="tc-badge ${statusClass}">${d.status}</span>
            </div>
          </div>
        `;
      }).join('');
    }

    if (statusEl) {
      if (res.success) {
        statusEl.textContent = `🎉 Xuất sắc! Vượt qua toàn bộ ${res.total} test case (Tốc độ TB: ${res.avg_time_ms}ms).`;
        statusEl.className = 'status-msg success';
      } else {
        statusEl.textContent = `Kiểm thử hoàn tất: Vượt qua ${res.passed}/${res.total} test case.`;
        statusEl.className = 'status-msg warning';
      }
    }

  } catch (err) {
    if (statusEl) {
      statusEl.textContent = `Lỗi kiểm thử: ${err.message}`;
      statusEl.className = 'status-msg error';
    }
  } finally {
    btnRun.disabled = false;
    btnRun.textContent = originalText;
  }
}

/**
 * Nộp Bài Chính Thức (Manual Submit)
 */
async function submitContestBotAction() {
  if (isEditorLocked || !currentContest) return;

  const codeEl = document.getElementById('my-bot-code');
  const langEl = document.getElementById('my-bot-lang');
  const statusEl = document.getElementById('my-bot-status');
  const btnSub = document.getElementById('btn-contest-submit');

  const sourceCode = codeEl?.value || '';
  const language = langEl?.value || 'python';

  if (!sourceCode.trim()) {
    if (statusEl) {
      statusEl.textContent = 'Mã nguồn không được để trống.';
      statusEl.className = 'status-msg error';
    }
    return;
  }

  if (!confirm('Bạn có chắc chắn muốn chốt nộp bản thuật toán này làm bài thi chính thức?')) {
    return;
  }

  btnSub.disabled = true;
  const originalText = btnSub.textContent;
  btnSub.textContent = '🚀 Đang nộp bài...';

  try {
    const res = await api.submitContestBot(currentContest.id, {
      source_code: sourceCode,
      language: language
    });

    if (statusEl) {
      statusEl.textContent = `✅ ${res.message || 'Nộp bài chính thức thành công!'}`;
      statusEl.className = 'status-msg success';
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = `Lỗi nộp bài: ${err.message}`;
      statusEl.className = 'status-msg error';
    }
  } finally {
    btnSub.disabled = false;
    btnSub.textContent = originalText;
  }
}

/**
 * Đấu thử với Máy (Practice Session)
 */
async function practiceDuelAction() {
  const codeEl = document.getElementById('my-bot-code');
  const langEl = document.getElementById('my-bot-lang');
  const gameSelect = document.getElementById('game-select');
  const statusEl = document.getElementById('my-bot-status');
  const btnPractice = document.getElementById('btn-practice-duel');

  const sourceCode = codeEl?.value || '';
  const language = langEl?.value || 'python';
  const gameSlug = gameSelect?.value || currentContest?.game_slug || 'default';

  if (!sourceCode.trim()) {
    if (statusEl) {
      statusEl.textContent = 'Vui lòng nhập code trước khi đấu thử.';
      statusEl.className = 'status-msg error';
    }
    return;
  }

  btnPractice.disabled = true;
  const oldText = btnPractice.textContent;
  btnPractice.textContent = '⏳ Đang đấu...';

  try {
    const res = await api.runPractice(sourceCode, language, 'random_bot', gameSlug);
    if (res && res.success) {
      const winner = res.summary?.winner_name || 'Hòa';
      const reason = res.summary?.reason || 'Kết thúc ván đấu';
      if (statusEl) {
        statusEl.textContent = `Kết quả đấu thử: ${winner} - ${reason}`;
        statusEl.className = 'status-msg success';
      }

      // Đổi sang tab bàn cờ và phát replay
      switchRightTab('board');
      playMatchReplay(res);
    } else {
      throw new Error(res?.error || 'Đấu thử thất bại.');
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = `Lỗi đấu thử: ${err.message}`;
      statusEl.className = 'status-msg error';
    }
  } finally {
    btnPractice.disabled = false;
    btnPractice.textContent = oldText;
  }
}

/**
 * Tải bảng xếp hạng Contest Leaderboard
 */
async function loadContestLeaderboard(contestId) {
  const tbody = document.getElementById('contest-leaderboard-body');
  if (!tbody) return;

  try {
    const res = await api.getContestLeaderboard(contestId);
    const list = res.leaderboard || [];

    if (!list.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Chưa có kết quả vòng đấu. Vui lòng chờ đến khi hết giờ thi đấu.</td></tr>';
      return;
    }

    tbody.innerHTML = list.map((item, idx) => {
      const rank = item.rank || idx + 1;
      const rankClass = rank <= 3 ? `rank-${rank}` : '';
      return `
        <tr>
          <td><span class="rank-pill ${rankClass}">${rank}</span></td>
          <td><strong>${escapeHtml(item.display_name || item.username)}</strong> (@${escapeHtml(item.username)})</td>
          <td style="color: #4ade80; font-weight: 700;">${item.wins || 0}</td>
          <td style="color: #facc15; font-weight: 700;">${item.draws || 0}</td>
          <td style="color: #f43f5e; font-weight: 700;">${item.losses || 0}</td>
          <td><strong style="color: #38bdf8; font-size: 1rem;">${item.points || 0}</strong></td>
          <td style="font-family: monospace;">${item.avg_speed_ms || 0} ms</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="color: var(--danger); text-align: center;">Lỗi tải bảng xếp hạng: ${err.message}</td></tr>`;
  }
}

/**
 * Chuyển tab panel bên phải: Bàn cờ vs Bảng xếp hạng
 */
function switchRightTab(tabName) {
  const tabBoard = document.getElementById('tab-btn-board');
  const tabLb = document.getElementById('tab-btn-leaderboard');
  const contentBoard = document.getElementById('tab-content-board');
  const contentLb = document.getElementById('tab-content-leaderboard');

  if (tabName === 'board') {
    tabBoard?.classList.add('active');
    tabLb?.classList.remove('active');
    if (contentBoard) contentBoard.style.display = 'block';
    if (contentLb) contentLb.style.display = 'none';
  } else {
    tabLb?.classList.add('active');
    tabBoard?.classList.remove('active');
    if (contentLb) contentLb.style.display = 'block';
    if (contentBoard) contentBoard.style.display = 'none';
    if (currentContest) loadContestLeaderboard(currentContest.id);
  }
}

/**
 * Trình diễn ván đấu trên bàn cờ (Replay Engine)
 */
function renderBoard(size = 9) {
  const container = document.getElementById('board-container');
  if (!container) return;
  container.style.gridTemplateColumns = `repeat(${size}, var(--cell-size))`;
  container.style.gridTemplateRows = `repeat(${size}, var(--cell-size))`;
  container.innerHTML = '';

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const cell = document.createElement('div');
      cell.className = `cell ${(r + c) % 2 === 0 ? 'cell-light' : 'cell-dark'}`;
      cell.id = `cell-${r}-${c}`;
      container.appendChild(cell);
    }
  }
}

function playMatchReplay(matchData) {
  currentReplay = matchData.replay || [];
  replayStep = 0;
  const seek = document.getElementById('replay-seek');
  if (seek) {
    seek.disabled = false;
    seek.max = currentReplay.length;
    seek.value = 0;
  }
  renderBoard(9);
  stepReplayForward();
}

function stepReplayForward() {
  if (!currentReplay || replayStep >= currentReplay.length) {
    isPlaying = false;
    const toggleBtn = document.getElementById('replay-toggle');
    if (toggleBtn) toggleBtn.textContent = '▶ Tiếp tục';
    return;
  }

  const turn = currentReplay[replayStep];
  const roundEl = document.getElementById('display-round');
  const playerEl = document.getElementById('display-player');
  const seek = document.getElementById('replay-seek');

  if (roundEl) roundEl.textContent = turn.round || (replayStep + 1);
  if (playerEl) playerEl.textContent = `P${turn.player}`;
  if (seek) seek.value = replayStep + 1;

  if (turn.move && typeof turn.move.row === 'number' && typeof turn.move.col === 'number') {
    const cell = document.getElementById(`cell-${turn.move.row}-${turn.move.col}`);
    if (cell) {
      cell.className = `cell piece-p${turn.player}`;
      cell.textContent = turn.player === 0 ? 'X' : 'O';
    }
  }

  replayStep++;
  const speedEl = document.getElementById('replay-speed');
  const speed = parseFloat(speedEl?.value || '1.0');
  const delay = Math.max(100, Math.round(500 / speed));

  if (isPlaying) {
    replayTimer = setTimeout(stepReplayForward, delay);
  }
}

/**
 * Nạp thông tin cuộc thi hiện tại từ backend
 */
async function loadContestData() {
  try {
    const res = await api.getActiveContest();
    if (!res || !res.success || !res.contest) return;

    currentContest = res.contest;
    document.getElementById('contest-title').textContent = `🏆 ${currentContest.title}`;
    document.getElementById('contest-duration').textContent = `${currentContest.duration_minutes} phút`;
    document.getElementById('contest-ram').textContent = `${currentContest.max_memory_mb || 128}MB`;
    document.getElementById('contest-timeout').textContent = `${currentContest.run_timeout_sec || 2.0}s`;

    // Đồng bộ thời gian đếm ngược
    initCountdown(currentContest.remaining_seconds, currentContest.status);

    // Tải danh sách test cases hiển thị
    const listContainer = document.getElementById('test-cases-list');
    if (listContainer && res.test_cases) {
      listContainer.innerHTML = res.test_cases.map(tc => `
        <div class="test-case-row">
          <div class="test-case-name">${escapeHtml(tc.name)}</div>
          <div class="tc-metrics">
            <span>⏱ Giới hạn: ${tc.timeout_ms || 1000}ms</span>
            <span class="tc-badge" style="background: rgba(255,255,255,0.1); color: var(--text-muted);">SẴN SÀNG</span>
          </div>
        </div>
      `).join('');
    }

    // Khôi phục mã nguồn theo thứ tự ưu tiên
    const codeEl = document.getElementById('my-bot-code');
    const langEl = document.getElementById('my-bot-lang');
    if (codeEl) {
      const serverDraft = res.my_draft;
      const localDraft = localStorage.getItem(`icpc_draft_${currentContest.id}`);

      if (serverDraft && serverDraft.source_code) {
        codeEl.value = serverDraft.source_code;
        if (langEl && serverDraft.language) langEl.value = serverDraft.language;
        blurCount = serverDraft.blur_count || 0;
        totalBlurSec = serverDraft.total_blur_sec || 0;
        lastSyncedCode = serverDraft.source_code;
      } else if (localDraft) {
        codeEl.value = localDraft;
      } else {
        // Code mặc định mẫu Caro
        codeEl.value = `import sys
import json
import random

def get_move(state):
    board = state.get("board", [])
    empty_cells = []
    for r in range(len(board)):
        for c in range(len(board[r])):
            if board[r][c] is None:
                empty_cells.append({"row": r, "col": c})
    if empty_cells:
        return random.choice(empty_cells)
    return {"action": "PASS"}

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            state = json.loads(line.strip())
            move = get_move(state)
            print(json.dumps(move), flush=True)
        except Exception:
            print(json.dumps({"action": "PASS"}), flush=True)

if __name__ == "__main__":
    main()
`;
      }
    }

  } catch (err) {
    console.error('Lỗi khi tải thông tin contest:', err);
    document.getElementById('contest-title').textContent = '🏆 Giải Đấu Thuật Toán Bot ICPC';
  }
}

/**
 * Nạp danh sách game vào selector
 */
async function loadGames() {
  const gameSelect = document.getElementById('game-select');
  if (!gameSelect) return;
  try {
    const res = await api.getActiveGames();
    const games = res.games || [];
    gameSelect.innerHTML = '';
    if (!games.length) {
      gameSelect.innerHTML = '<option value="default">Caro 9x9 tiêu chuẩn</option>';
      return;
    }
    games.forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.slug;
      opt.textContent = g.name;
      gameSelect.appendChild(opt);
    });
  } catch (err) {
    gameSelect.innerHTML = '<option value="default">Caro 9x9 tiêu chuẩn</option>';
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

// Gắn sự kiện khi DOM tải hoàn tất
document.addEventListener('DOMContentLoaded', () => {
  renderBoard(9);
  loadGames();
  loadContestData();
  initAntiCheatProctor();
  initAutoSave();

  // Nút hành động
  document.getElementById('btn-run-tests')?.addEventListener('click', runTestSuiteAction);
  document.getElementById('btn-contest-submit')?.addEventListener('click', submitContestBotAction);
  document.getElementById('btn-practice-duel')?.addEventListener('click', practiceDuelAction);

  // Tabs panel phải
  document.getElementById('tab-btn-board')?.addEventListener('click', () => switchRightTab('board'));
  document.getElementById('tab-btn-leaderboard')?.addEventListener('click', () => switchRightTab('leaderboard'));
  document.getElementById('btn-refresh-leaderboard')?.addEventListener('click', () => {
    if (currentContest) loadContestLeaderboard(currentContest.id);
  });

  // Replay controls
  const toggleBtn = document.getElementById('replay-toggle');
  toggleBtn?.addEventListener('click', () => {
    isPlaying = !isPlaying;
    toggleBtn.textContent = isPlaying ? '⏸ Tạm dừng' : '▶ Tiếp tục';
    if (isPlaying) stepReplayForward();
  });

  document.getElementById('replay-reset')?.addEventListener('click', () => {
    isPlaying = false;
    if (toggleBtn) toggleBtn.textContent = '▶ Tiếp tục';
    replayStep = 0;
    renderBoard(9);
    const seek = document.getElementById('replay-seek');
    if (seek) seek.value = 0;
  });
});
