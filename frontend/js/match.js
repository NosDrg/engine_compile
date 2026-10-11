// js/match.js
import { api } from './api.js';

export class MatchController {
  constructor(boardView) {
    this.boardView = boardView;
    this.playbackInterval = null;

    this.roundEl = document.getElementById('display-round');
    this.playerEl = document.getElementById('display-player');
    this.timeEl = document.getElementById('display-time');
    this.resultBox = document.getElementById('match-result');
    this.resultTitle = document.getElementById('result-title');
    this.resultDesc = document.getElementById('result-desc');

    this.winAudio = new Audio('assets/icons/winners.mp3');
  }

  async start(bot0, bot1) {
    this.resultBox.classList.add('hidden');
    this.stopPlayback();

    // 1. Gửi lệnh chạy trận đấu
    const res = await api.createMatch(bot0.sub_id, bot1.sub_id);
    if (!res.success) {
      alert(`Không thể tổ chức trận đấu: ${res.message || res.detail || 'Lỗi không xác định'}`);
      return;
    }

    const replayList = res.replay || [];
    
    // Nếu cả 2 không có nước đi nào (vd lỗi biên dịch)
    if (replayList.length === 0) {
      this.showResult(res.summary?.winner_slot, res.summary?.reason);
      return;
    }

    // 2. Tái hiện lại từng nước đi trên bàn cờ
    this.playReplay(replayList, res.summary);
  }

  playReplay(replayList, summary) {
    let step = 0;
    
    // Tạo bàn cờ mô phỏng ban đầu
    let boardState = this.createInitialBoardState();
    this.boardView.render(boardState);

    this.playbackInterval = setInterval(() => {
      if (step >= replayList.length) {
        this.stopPlayback();
        this.showResult(summary.winner_slot, summary.reason);
        return;
      }

      const moveRecord = replayList[step];
      const m = moveRecord.move_obj;

      // Cập nhật vị trí quân cờ
      const movingPiece = boardState[m.from_y][m.from_x];
      boardState[m.from_y][m.from_x] = null;
      boardState[m.to_y][m.to_x] = movingPiece;

      // Hiển thị thông số
      this.roundEl.textContent = moveRecord.round;
      this.playerEl.textContent = moveRecord.player === 0 ? 'Player 0 (Xanh dương)' : 'Player 1 (Đỏ)';
      this.timeEl.textContent = `${moveRecord.elapsed_ms}ms`;

      // Render lại bàn cờ với highlight
      this.boardView.render(boardState, m);

      step++;
    }, 450); // Phát mỗi nước cách nhau 450ms
  }

  stopPlayback() {
    if (this.playbackInterval) {
      clearInterval(this.playbackInterval);
      this.playbackInterval = null;
    }
  }

  createInitialBoardState() {
    // Tạo lưới ma trận trống 9x9
    const grid = [];
    for (let y = 0; y < 9; y++) {
      grid.push(new Array(9).fill(null));
    }
    return grid;
  }

  showResult(winnerSlot, reason) {
    this.resultBox.classList.remove('hidden');
    let winnerText = 'HÒA';
    if (winnerSlot === 0) winnerText = 'Player 0 (Xanh dương)';
    else if (winnerSlot === 1) winnerText = 'Player 1 (Đỏ)';

    this.resultTitle.textContent = `Người thắng: ${winnerText}`;
    this.resultDesc.textContent = `Lý do: ${reason}`;

    // Phát âm thanh chiến thắng
    this.winAudio.play().catch(() => {});
  }
}