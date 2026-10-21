// frontend/js/admin_games.js
import { api } from './api.js';
import { refreshUser } from './auth.js';

const SAMPLE_REFEREE = `# referee.py - Default Referee Protocol Template
def init_game() -> dict:
    """Khởi tạo trạng thái ban đầu của bàn cờ."""
    return {
        "board": [[None for _ in range(9)] for _ in range(9)],
        "turn": 0,
        "max_turns": 81
    }

def validate_move(state: dict, move: dict, player_slot: int) -> bool:
    """Kiểm tra xem nước đi của player_slot có hợp lệ hay không."""
    if not isinstance(move, dict):
        return False
    row = move.get("row")
    col = move.get("col")
    if row is None or col is None:
        return False
    if not isinstance(row, int) or not isinstance(col, int):
        return False
    if not (0 <= row < 9 and 0 <= col < 9):
        return False
    board = state.get("board", [])
    if row >= len(board) or col >= len(board[row]):
        return False
    return board[row][col] is None

def apply_move(state: dict, move: dict, player_slot: int) -> tuple:
    """
    Áp dụng nước đi vào state, kiểm tra thắng thua.
    Trả về: (new_state, winner_slot, reason)
    - new_state: dict trạng thái mới
    - winner_slot: 0, 1 nếu có người thắng; -1 nếu hòa; None nếu ván đấu tiếp tục
    - reason: lý do hoặc thông điệp nước đi
    """
    import copy
    new_state = copy.deepcopy(state)
    r = int(move["row"])
    c = int(move["col"])
    new_state["board"][r][c] = player_slot
    new_state["turn"] = int(new_state.get("turn", 0)) + 1

    board = new_state["board"]
    size = len(board)
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dr, dc in directions:
        count = 1
        nr, nc = r + dr, c + dc
        while 0 <= nr < size and 0 <= nc < size and board[nr][nc] == player_slot:
            count += 1
            nr += dr
            nc += dc
        nr, nc = r - dr, c - dc
        while 0 <= nr < size and 0 <= nc < size and board[nr][nc] == player_slot:
            count += 1
            nr -= dr
            nc -= dc
        if count >= 5:
            return new_state, player_slot, f"Người chơi {player_slot} kết nối chuỗi 5 điểm!"

    if new_state["turn"] >= int(new_state.get("max_turns", 81)):
        return new_state, -1, "Hòa cờ - Đã hết lượt đi tối đa."

    return new_state, None, "Nước đi hợp lệ."
`;

const SAMPLE_STARTER_BOT = `import sys
import json
import random

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            state = json.loads(line.strip())
            board = state.get("board", [])
            empty_cells = []
            for r in range(len(board)):
                for c in range(len(board[r])):
                    if board[r][c] is None:
                        empty_cells.append({"row": r, "col": c})
            if empty_cells:
                # Chọn nước đi ngẫu nhiên từ danh sách ô trống
                move = random.choice(empty_cells)
                print(json.dumps(move), flush=True)
            else:
                print(json.dumps({"action": "PASS"}), flush=True)
        except Exception:
            print(json.dumps({"action": "PASS"}), flush=True)

if __name__ == "__main__":
    main()
`;

document.addEventListener('DOMContentLoaded', async () => {
  const user = await refreshUser();
  if (!user || user.role !== 'admin') {
    location.href = '/login.html?redirect=/admin/games.html';
    return;
  }

  // DOM Elements - Games
  const selectGame = document.getElementById('select-game');
  const gameForm = document.getElementById('game-form');
  const gameSlug = document.getElementById('game-slug');
  const gameName = document.getElementById('game-name');
  const gameBoardType = document.getElementById('game-board-type');
  const gameIsActive = document.getElementById('game-is-active');
  const gameDescription = document.getElementById('game-description');
  const gameRefereeCode = document.getElementById('game-referee-code');
  const gameStarterCode = document.getElementById('game-starter-code');
  const btnTestReferee = document.getElementById('btn-test-referee');
  const btnLoadSampleRef = document.getElementById('btn-load-sample-referee');
  const btnLoadSampleBot = document.getElementById('btn-load-sample-bot');
  const dryrunPanel = document.getElementById('dryrun-panel');
  const dryrunStatus = document.getElementById('dryrun-status');
  const dryrunJson = document.getElementById('dryrun-json');
  const saveStatusMsg = document.getElementById('save-status-msg');
  const statusAlert = document.getElementById('status-alert');

  // DOM Elements - Runtimes
  const runtimesTbody = document.getElementById('runtimes-tbody');
  const runtimeForm = document.getElementById('runtime-form');
  const runtimeFormTitle = document.getElementById('runtime-form-title');
  const rtId = document.getElementById('rt-id');
  const rtName = document.getElementById('rt-name');
  const rtExtension = document.getElementById('rt-extension');
  const rtCompile = document.getElementById('rt-compile');
  const rtRun = document.getElementById('rt-run');
  const rtTimeout = document.getElementById('rt-timeout');
  const rtMemory = document.getElementById('rt-memory');
  const rtIsEnabled = document.getElementById('rt-is-enabled');
  const btnResetRuntime = document.getElementById('btn-reset-runtime');
  const runtimeStatusMsg = document.getElementById('runtime-status-msg');

  let gamesList = [];
  let runtimesList = [];

  function showAlert(msg, isError = false) {
    statusAlert.textContent = msg;
    statusAlert.style.color = isError ? 'var(--danger)' : 'var(--success)';
  }

  function setGameFormData(game = null) {
    if (game) {
      gameSlug.value = game.slug || '';
      gameSlug.readOnly = true;
      gameName.value = game.name || '';
      gameBoardType.value = game.board_type || 'grid_9x9';
      gameIsActive.checked = Boolean(game.is_active);
      gameDescription.value = game.description || '';
      gameRefereeCode.value = game.referee_code || '';
      gameStarterCode.value = game.starter_bot_code || '';
    } else {
      gameSlug.value = '';
      gameSlug.readOnly = false;
      gameName.value = '';
      gameBoardType.value = 'grid_9x9';
      gameIsActive.checked = true;
      gameDescription.value = '';
      gameRefereeCode.value = SAMPLE_REFEREE;
      gameStarterCode.value = SAMPLE_STARTER_BOT;
    }
    dryrunPanel.style.display = 'none';
    saveStatusMsg.textContent = '';
  }

  async function loadGames() {
    try {
      const res = await api.adminGetGames();
      gamesList = res.games || [];
      selectGame.innerHTML = '<option value="NEW">+ Tạo Game Mới</option>';
      gamesList.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.slug;
        opt.textContent = `${g.name} (${g.slug}) ${g.is_active ? '· [Active]' : '· [Tắt]'}`;
        selectGame.appendChild(opt);
      });

      if (gamesList.length > 0) {
        selectGame.value = gamesList[0].slug;
        setGameFormData(gamesList[0]);
      } else {
        setGameFormData(null);
      }
    } catch (err) {
      showAlert('Không thể tải danh sách game: ' + err.message, true);
    }
  }

  selectGame.addEventListener('change', () => {
    const val = selectGame.value;
    if (val === 'NEW') {
      setGameFormData(null);
    } else {
      const found = gamesList.find(g => g.slug === val);
      setGameFormData(found || null);
    }
  });

  btnLoadSampleRef?.addEventListener('click', () => {
    if (confirm('Nạp mã mẫu trọng tài tiêu chuẩn (Caro 9x9)?')) {
      gameRefereeCode.value = SAMPLE_REFEREE;
    }
  });

  btnLoadSampleBot?.addEventListener('click', () => {
    if (confirm('Nạp mã mẫu bot cho thí sinh?')) {
      gameStarterCode.value = SAMPLE_STARTER_BOT;
    }
  });

  btnTestReferee.addEventListener('click', async () => {
    const code = gameRefereeCode.value.trim();
    if (!code) {
      alert('Vui lòng nhập mã trọng tài trước khi kiểm thử.');
      return;
    }

    btnTestReferee.disabled = true;
    btnTestReferee.textContent = '⏳ Đang kiểm thử...';
    dryrunPanel.style.display = 'block';
    dryrunStatus.textContent = 'Đang chạy mô phỏng init_game() và validate_move()...';
    dryrunStatus.style.color = 'var(--text-muted)';
    dryrunJson.textContent = '';

    try {
      const res = await api.adminTestReferee(code);
      dryrunStatus.textContent = '✅ Dry-Run thành công!';
      dryrunStatus.style.color = 'var(--success)';
      dryrunJson.textContent = JSON.stringify(res, null, 2);
    } catch (err) {
      dryrunStatus.textContent = '❌ Lỗi kiểm thử: ' + err.message;
      dryrunStatus.style.color = 'var(--danger)';
      dryrunJson.textContent = err.message;
    } finally {
      btnTestReferee.disabled = false;
      btnTestReferee.textContent = '🧪 Chạy thử Trọng tài (Dry-Run)';
    }
  });

  gameForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      slug: gameSlug.value.trim(),
      name: gameName.value.trim(),
      board_type: gameBoardType.value,
      description: gameDescription.value.trim(),
      referee_code: gameRefereeCode.value,
      starter_bot_code: gameStarterCode.value,
      is_active: gameIsActive.checked ? 1 : 0
    };

    if (!payload.slug || !payload.name) {
      alert('Vui lòng điền đầy đủ Tên game và Slug.');
      return;
    }

    const btnSubmit = document.getElementById('btn-save-game');
    btnSubmit.disabled = true;
    saveStatusMsg.textContent = 'Đang kiểm tra và lưu...';
    saveStatusMsg.style.color = 'var(--text-muted)';

    try {
      const res = await api.adminSaveGame(payload);
      saveStatusMsg.textContent = '✅ ' + (res.message || 'Lưu thành công!');
      saveStatusMsg.style.color = 'var(--success)';
      showAlert(`Trò chơi '${payload.name}' đã được lưu thành công.`);
      const savedSlug = payload.slug;
      await loadGames();
      selectGame.value = savedSlug;
      const found = gamesList.find(g => g.slug === savedSlug);
      setGameFormData(found);
    } catch (err) {
      saveStatusMsg.textContent = '❌ Lỗi: ' + err.message;
      saveStatusMsg.style.color = 'var(--danger)';
      showAlert('Lỗi khi lưu trò chơi: ' + err.message, true);
    } finally {
      btnSubmit.disabled = false;
    }
  });

  // --- Runtime Management ---
  async function loadRuntimes() {
    try {
      const res = await api.adminGetRuntimes();
      runtimesList = res.runtimes || [];
      renderRuntimesTable();
    } catch (err) {
      runtimesTbody.innerHTML = `<tr><td colspan="9" style="color:var(--danger)">Lỗi tải runtime: ${err.message}</td></tr>`;
    }
  }

  function renderRuntimesTable() {
    if (!runtimesList.length) {
      runtimesTbody.innerHTML = '<tr><td colspan="9">Chưa có runtime nào được cấu hình.</td></tr>';
      return;
    }

    runtimesTbody.innerHTML = runtimesList.map(r => `
      <tr>
        <td><code>${r.id}</code></td>
        <td><strong>${r.name}</strong></td>
        <td>.${r.extension}</td>
        <td><code>${r.compile_cmd || '(None - Thông dịch)'}</code></td>
        <td><code>${r.run_cmd}</code></td>
        <td>${r.timeout_sec}s</td>
        <td>${r.memory_limit_mb} MB</td>
        <td>${r.is_enabled ? '<span class="badge" style="background:#059669;">Bật</span>' : '<span class="badge" style="background:#dc2626;">Tắt</span>'}</td>
        <td>
          <button class="btn btn-ghost btn-sm" data-edit-rt="${r.id}">Sửa</button>
        </td>
      </tr>
    `).join('');

    runtimesTbody.querySelectorAll('[data-edit-rt]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.editRt;
        const rt = runtimesList.find(item => item.id === id);
        if (rt) {
          rtId.value = rt.id;
          rtId.readOnly = true;
          rtName.value = rt.name;
          rtExtension.value = rt.extension;
          rtCompile.value = rt.compile_cmd || '';
          rtRun.value = rt.run_cmd;
          rtTimeout.value = rt.timeout_sec;
          rtMemory.value = rt.memory_limit_mb;
          rtIsEnabled.checked = Boolean(rt.is_enabled);
          runtimeFormTitle.textContent = `Chỉnh sửa Runtime: ${rt.name} (${rt.id})`;
          runtimeForm.scrollIntoView({ behavior: 'smooth' });
        }
      });
    });
  }

  btnResetRuntime?.addEventListener('click', () => {
    rtId.value = '';
    rtId.readOnly = false;
    rtName.value = '';
    rtExtension.value = '';
    rtCompile.value = '';
    rtRun.value = '';
    rtTimeout.value = 2.0;
    rtMemory.value = 128;
    rtIsEnabled.checked = true;
    runtimeFormTitle.textContent = '+ Thêm / Cập nhật Trình biên dịch (Runtime)';
    runtimeStatusMsg.textContent = '';
  });

  runtimeForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      id: rtId.value.trim().toLowerCase(),
      name: rtName.value.trim(),
      extension: rtExtension.value.trim().replace(/^\\./, ''),
      compile_cmd: rtCompile.value.trim(),
      run_cmd: rtRun.value.trim(),
      timeout_sec: parseFloat(rtTimeout.value) || 2.0,
      memory_limit_mb: parseInt(rtMemory.value) || 128,
      is_enabled: rtIsEnabled.checked ? 1 : 0
    };

    runtimeStatusMsg.textContent = 'Đang lưu runtime...';
    try {
      await api.adminSaveRuntime(payload);
      runtimeStatusMsg.textContent = '✅ Đã lưu cấu hình runtime!';
      runtimeStatusMsg.style.color = 'var(--success)';
      await loadRuntimes();
    } catch (err) {
      runtimeStatusMsg.textContent = '❌ ' + err.message;
      runtimeStatusMsg.style.color = 'var(--danger)';
    }
  });

  // Khởi động
  await Promise.all([loadGames(), loadRuntimes()]);
});
