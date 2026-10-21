// frontend/js/arena.js
import { api } from './api.js';

let activeGames = [];

/**
 * Reset bàn cờ theo loại kích thước (grid_9x9 hoặc grid_15x15)
 */
export function resetBoardForType(boardType = 'grid_9x9') {
  const container = document.getElementById('board-container');
  if (!container) return;

  const size = boardType === 'grid_15x15' ? 15 : 9;
  const cellSize = boardType === 'grid_15x15' ? '28px' : 'var(--cell-size)';

  container.style.gridTemplateColumns = `repeat(${size}, ${cellSize})`;
  container.style.gridTemplateRows = `repeat(${size}, ${cellSize})`;

  if (window.matchController && window.matchController.boardView) {
    window.matchController.boardView.size = size;
    window.matchController.boardView.initGrid();
  } else {
    container.innerHTML = '';
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const cell = document.createElement('div');
        const patternClass = (x + y) % 2 === 0 ? 'cell-light' : 'cell-dark';
        cell.className = `cell ${patternClass}`;
        cell.dataset.x = x;
        cell.dataset.y = y;
        container.appendChild(cell);
      }
    }
  }
}

/**
 * Khởi tạo selector chọn game từ backend API
 */
export async function initGameSelector() {
  const gameSelect = document.getElementById('game-select');
  if (!gameSelect) return;

  gameSelect.innerHTML = '<option value="">Đang tải danh sách game...</option>';

  try {
    const res = await api.getActiveGames();
    activeGames = res.games || [];
    gameSelect.innerHTML = '';

    if (!activeGames.length) {
      const opt = document.createElement('option');
      opt.value = 'default';
      opt.textContent = 'Caro 9x9 (Mặc định)';
      gameSelect.appendChild(opt);
      return;
    }

    activeGames.forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.slug;
      opt.textContent = g.name;
      gameSelect.appendChild(opt);
    });

    // Khi nạp xong, chọn game đầu tiên và cập nhật code editor nếu chưa có nội dung
    const initialGame = activeGames[0];
    const codeEl = document.getElementById('my-bot-code');
    if (codeEl && !codeEl.value.trim() && initialGame.starter_bot_code) {
      codeEl.value = initialGame.starter_bot_code;
    }
    resetBoardForType(initialGame.board_type || 'grid_9x9');

  } catch (err) {
    console.error('Lỗi khi tải danh sách game:', err);
    gameSelect.innerHTML = '<option value="default">Caro 9x9 (Mặc định)</option>';
  }

  // Sự kiện khi người dùng đổi game
  gameSelect.addEventListener('change', () => {
    const selectedSlug = gameSelect.value;
    const game = activeGames.find(g => g.slug === selectedSlug);
    if (!game) return;

    const codeEl = document.getElementById('my-bot-code');
    if (codeEl && game.starter_bot_code) {
      codeEl.value = game.starter_bot_code;
    }

    resetBoardForType(game.board_type || 'grid_9x9');
  });
}

/**
 * Gắn sự kiện cho nút Đấu thử với Máy
 */
function bindPracticeDuel() {
  const btnPractice = document.getElementById('btn-practice-duel');
  if (!btnPractice) return;

  btnPractice.addEventListener('click', async (event) => {
    const codeEl = document.getElementById('my-bot-code');
    const langEl = document.getElementById('my-bot-lang');
    const gameSelect = document.getElementById('game-select');
    const statusEl = document.getElementById('my-bot-status');

    const sourceCode = codeEl?.value || '';
    const language = langEl?.value || 'python';
    const gameSlug = gameSelect?.value || 'default';

    if (!sourceCode.trim()) {
      if (statusEl) {
        statusEl.textContent = 'Vui lòng nhập mã nguồn thuật toán trước khi đấu thử.';
        statusEl.className = 'status-msg error';
      }
      return;
    }

    const btn = event.currentTarget;
    btn.disabled = true;
    const oldText = btn.textContent;
    btn.textContent = '⏳ Đang đấu thử...';

    if (statusEl) {
      statusEl.textContent = `Đang khởi tạo trận đấu thử game [${gameSlug}]...`;
      statusEl.className = 'status-msg';
    }

    try {
      const res = await api.runPractice(sourceCode, language, 'random_bot', gameSlug);
      if (res && res.success) {
        const winner = res.summary?.winner_name || 'Hòa';
        const reason = res.summary?.reason || 'Ván đấu kết thúc.';
        if (statusEl) {
          statusEl.textContent = `Kết quả đấu thử: ${winner} (${reason})`;
          statusEl.className = 'status-msg success';
        }

        // Phát lại ván đấu trên bàn cờ nếu MatchController sẵn sàng
        if (window.matchController && typeof window.matchController.playReplay === 'function') {
          window.matchController.playReplay(res);
        }
      } else {
        throw new Error(res?.error || 'Trận đấu thử không thành công.');
      }
    } catch (err) {
      if (statusEl) {
        statusEl.textContent = `Lỗi đấu thử: ${err.message}`;
        statusEl.className = 'status-msg error';
      }
    } finally {
      btn.disabled = false;
      btn.textContent = oldText;
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initGameSelector();
  bindPracticeDuel();
});
