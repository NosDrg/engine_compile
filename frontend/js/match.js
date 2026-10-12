// frontend/js/match.js
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

    this.winAudio = new Audio('assets/winners.mp3');
  }

  async start(bot0, bot1) {
    this.resultBox.classList.add('hidden');
    this.stopPlayback();
    this.boardView.clearPieces(); // Giữ nguyên các khối block, chỉ dọn sạch quân cũ

    // Gọi API Duel
    const res = await api.createMatch(bot0.sub_id, bot1.sub_id);
    console.log("Dữ liệu trận đấu trả về từ Server:", res);

    if (!res || !res.success) {
      alert(`Không thể tổ chức trận đấu: ${res?.message || res?.detail || 'Lỗi không xác định'}`);
      return;
    }

    const replayList = res.replay || [];
    // Nếu backend chưa gửi initial_board, dùng hàm sinh bàn cờ chuẩn luật[cite: 13]
    const initialBoard = res.initial_board || res.board || this.generateStandardInitialBoard(replayList);

    // Vẽ ngay lập tức quân cờ lúc bắt đầu trận
    this.boardView.render(initialBoard);

    if (replayList.length === 0) {
      this.showResult(res.summary?.winner_slot, res.summary?.reason);
      return;
    }

    // Chạy Replay từng bước
    this.playReplay(initialBoard, replayList, res.summary);
  }

  playReplay(initialBoard, replayList, summary) {
    let step = 0;
    let boardState = JSON.parse(JSON.stringify(initialBoard));

    this.playbackInterval = setInterval(() => {
      if (step >= replayList.length) {
        this.stopPlayback();
        this.showResult(summary?.winner_slot, summary?.reason);
        return;
      }

      const moveRecord = replayList[step];
      const m = moveRecord.move_obj;

      if (boardState[m.from_y] && boardState[m.from_y][m.from_x]) {
        const movingPiece = boardState[m.from_y][m.from_x];
        boardState[m.from_y][m.from_x] = null;
        boardState[m.to_y][m.to_x] = movingPiece;
      }

      this.roundEl.textContent = moveRecord.round;
      this.playerEl.textContent = moveRecord.player === 0 ? 'Player 0 (Xanh dương)' : 'Player 1 (Đỏ)';
      this.timeEl.textContent = `${moveRecord.elapsed_ms || 0}ms`;

      // Cập nhật bàn cờ và vẽ highlight nước đi
      this.boardView.render(boardState, m);

      step++;
    }, 450);
  }

  stopPlayback() {
    if (this.playbackInterval) {
      clearInterval(this.playbackInterval);
      this.playbackInterval = null;
    }
  }

  /**
   * Tạo bàn cờ ban đầu chuẩn 9 quân mỗi bên nếu backend không trả về initial_board
   */
  generateStandardInitialBoard(replayList) {
    const b = Array.from({ length: 9 }, () => Array(9).fill(null));
    const types = ['Rock', 'Paper', 'Scissors', 'Rock', 'Paper', 'Scissors', 'Rock', 'Paper', 'Scissors'];
    const p0_pos = [
      [0,1], [0,2], [0,3],
      [1,0], [1,1], [1,2],
      [2,0], [2,1], [2,2]
    ];

    for (let i = 0; i < 9; i++) {
      const [y, x] = p0_pos[i];
      b[y][x] = { piece_type: types[i], owner: 0 };
      // Đối xứng gương cho Player 1
      b[8 - y][8 - x] = { piece_type: types[i], owner: 1 };
    }
    return b;
  }

  showResult(winnerSlot, reason) {
    this.resultBox.classList.remove('hidden');
    let winnerText = 'HÒA';
    if (winnerSlot === 0) winnerText = 'Player 0 (Xanh dương)';
    else if (winnerSlot === 1) winnerText = 'Player 1 (Đỏ)';

    this.resultTitle.textContent = `Người thắng: ${winnerText}`;
    this.resultDesc.textContent = `Lý do: ${reason}`;

    this.winAudio.play().catch(() => {});
  }
}