// frontend/js/match.js
import { api } from './api.js?v=2';

// Cache trước ảnh quân và block vào RAM trình duyệt để vẽ tức thì không bị trễ
const PRELOAD_IMAGES = [
  'assets/rock.png',
  'assets/paper.png',
  'assets/scissors.png',
  'assets/block1.jpg',
  'assets/block2.jpg'
];
PRELOAD_IMAGES.forEach(src => {
  const img = new Image();
  img.src = src;
});

export class MatchController {
  constructor(boardView) {
    this.boardView = boardView;
    this.playbackTimer = null;

    this.roundEl = document.getElementById('display-round');
    this.playerEl = document.getElementById('display-player');
    this.timeEl = document.getElementById('display-time');
    this.resultBox = document.getElementById('match-result');
    this.resultTitle = document.getElementById('result-title');
    this.resultDesc = document.getElementById('result-desc');

    this.winAudio = new Audio('assets/winners.mp3');
  }

  stopPlayback() {
    if (this.playbackTimer) {
      clearInterval(this.playbackTimer);
      this.playbackTimer = null;
    }
  }

  async start(bot0, bot1) {
    this.stopPlayback();
    this.resultBox.classList.add('hidden');

    // Reset hiển thị đồng hồ / thông số
    if (this.roundEl) this.roundEl.textContent = '0';
    if (this.playerEl) this.playerEl.textContent = 'Đang tải trận đấu...';
    if (this.timeEl) this.timeEl.textContent = '0ms';

    const res = await api.createMatch(bot0.sub_id, bot1.sub_id);
    console.log("==> Dữ liệu trận đấu:", res);

    if (!res || !res.success) {
      alert(`Không thể thi đấu: ${res?.message || res?.detail || res?.error || 'Lỗi không xác định'}`);
      return;
    }

    const replayList = res.replay || [];
    const initialBoard = res.initial_board || res.board;

    if (!initialBoard) {
      alert("Lỗi: Server không gửi initial_board!");
      return;
    }

    // 1. Render bàn cờ lúc bắt đầu (Round 0)
    let currentBoard = JSON.parse(JSON.stringify(initialBoard));
    this.boardView.render(currentBoard);

    if (replayList.length === 0) {
      this.showResult(res.summary?.winner_slot, res.summary?.reason);
      return;
    }

    // 2. Chạy từng bước (mỗi bước cách nhau 700ms để kịp nhìn rõ chuyển động)
    let stepIndex = 0;

    this.playbackTimer = setInterval(() => {
      if (stepIndex >= replayList.length) {
        this.stopPlayback();
        this.showResult(res.summary?.winner_slot, res.summary?.reason);
        return;
      }

      const item = replayList[stepIndex];
      const m = item.move_obj || item.move || item;

      const fromX = Number(m.from_x);
      const fromY = Number(m.from_y);
      const toX = Number(m.to_x);
      const toY = Number(m.to_y);

      // Cập nhật quân cờ trên bàn cờ ảo
      if (currentBoard[fromY] && currentBoard[fromY][fromX]) {
        const piece = currentBoard[fromY][fromX];
        currentBoard[fromY][fromX] = null;
        currentBoard[toY][toX] = piece; // Di chuyển tới ô mới (ghi đè quân bị ăn nếu có)
      } else {
        console.warn(`Ô xuất phát rỗng tại (${fromX}, ${fromY}) ở lượt ${stepIndex + 1}`);
      }

      // Cập nhật thông tin giao diện bộ đếm
      if (this.roundEl) this.roundEl.textContent = item.round ?? (stepIndex + 1);
      if (this.playerEl) {
        const p = item.player !== undefined ? item.player : item.player_id;
        this.playerEl.textContent = p === 0 ? 'Player 0 (Xanh dương)' : 'Player 1 (Đỏ)';
      }
      if (this.timeEl) {
        this.timeEl.textContent = `${item.elapsed_ms ?? item.execution_time_ms ?? 0}ms`;
      }

      // Vẽ lại bàn cờ và tô sáng ô vừa đi
      this.boardView.render(currentBoard, { from_x: fromX, from_y: fromY, to_x: toX, to_y: toY });

      stepIndex++;
    }, 700); // 700ms mỗi lượt
  }

  showResult(winnerSlot, reason) {
    this.resultBox.classList.remove('hidden');
    let winnerText = 'HÒA';
    if (winnerSlot === 0) winnerText = 'Player 0 (Xanh dương)';
    else if (winnerSlot === 1) winnerText = 'Player 1 (Đỏ)';

    this.resultTitle.textContent = `Người thắng: ${winnerText}`;
    this.resultDesc.textContent = `Lý do: ${reason || 'Trận đấu kết thúc'}`;

    this.winAudio.play().catch(() => {});
  }
}