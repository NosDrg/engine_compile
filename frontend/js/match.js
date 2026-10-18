// frontend/js/match.js
import { api } from './api.js';

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
    this.playbackSpeed = 1;
    this.paused = false;
    this.activeJobId = null;

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

    let res;
    try {
      const queued = await api.createMatch(bot0.sub_id, bot1.sub_id, Boolean(bot0.ranked), bot0.seed ?? null, bot0.map_id ?? 'classic');
      if (!queued.job_id) throw new Error(queued.error || 'Không tạo được lượt đấu.');
      this.activeJobId = queued.job_id;
      const cancelButton = document.getElementById('btn-cancel-match');
      if (cancelButton) { cancelButton.hidden = false; cancelButton.disabled = false; }
      if (this.playerEl) this.playerEl.textContent = 'Đang chờ engine…';
      for (let attempt = 0; attempt < 900; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const status = await api.getQueueJob(queued.job_id);
        if (status.job.status === 'cancelled') {
          if (this.playerEl) this.playerEl.textContent = 'Trận đã được hủy';
          this.activeJobId = null;
          if (cancelButton) cancelButton.hidden = true;
          return;
        }
        if (cancelButton) {
          cancelButton.hidden = status.job.status !== 'queued';
          cancelButton.disabled = status.job.status !== 'queued';
          cancelButton.textContent = status.job.status === 'running' ? 'Trận đang chạy' : 'Hủy trận đang chờ';
        }
        if (status.job.status === 'failed') throw new Error(status.job.error_text || status.job.result?.error || 'Trận đấu thất bại.');
        if (status.job.status === 'completed') { res = status.job.result; break; }
        if (this.playerEl) this.playerEl.textContent = status.job.status === 'running' ? 'Đang chạy trận…' : 'Đang chờ engine…';
      }
      if (!res) throw new Error('Trận đấu đã chờ quá lâu. Hãy xem lại lịch sử trận.');
      if (!res.success) throw new Error(res.error || 'Trận đấu thất bại.');
      this.activeJobId = null;
      if (cancelButton) cancelButton.hidden = true;
    } catch (error) {
      this.activeJobId = null;
      const cancelButton = document.getElementById('btn-cancel-match');
      if (cancelButton) cancelButton.hidden = true;
      alert(`Không thể thi đấu: ${error.message}`);
      if (this.playerEl) this.playerEl.textContent = 'Lỗi trận đấu';
      return;
    }

    this.playReplay(res);
  }

  async cancelWaitingMatch() {
    if (!this.activeJobId) return false;
    const result = await api.cancelQueueJob(this.activeJobId);
    return result.status === 'cancelled';
  }

  playReplay(res) {
    this.stopPlayback();
    this.resultBox.classList.add('hidden');
    const replayList = res.replay || [];
    const initialBoard = res.initial_board || res.board;

    if (!initialBoard) {
      alert("Lỗi: Server không gửi initial_board!");
      return;
    }

    // 1. Render bàn cờ lúc bắt đầu (Round 0)
    this.replayData = res;
    this.replayList = replayList;
    this.initialBoard = JSON.parse(JSON.stringify(initialBoard));
    this.stepIndex = 0;
    this.paused = false;
    this.boardView.render(JSON.parse(JSON.stringify(this.initialBoard)));
    this.updateReplayControls();

    if (replayList.length === 0) {
      this.showResult(res.summary?.winner_slot, res.summary?.reason);
      return;
    }

    // 2. Chạy từng bước (mỗi bước cách nhau 700ms để kịp nhìn rõ chuyển động)
    this.renderReplayStep(0);
    this.startTimer();
  }

  startTimer() {
    this.stopPlayback();
    if (!this.replayList?.length) return;
    this.playbackTimer = setInterval(() => {
      if (this.paused) return;
      if (this.stepIndex >= this.replayList.length) {
        this.stopPlayback();
        this.showResult(this.replayData.summary?.winner_slot, this.replayData.summary?.reason);
        return;
      }
      this.renderReplayStep(this.stepIndex + 1);
    }, 700 / this.playbackSpeed);
  }

  renderReplayStep(step) {
    this.stepIndex = Math.max(0, Math.min(step, this.replayList.length));
    const board = JSON.parse(JSON.stringify(this.initialBoard));
    let last = null;
    for (let i = 0; i < this.stepIndex; i++) {
      const move = this.replayList[i].move_obj || this.replayList[i].move || this.replayList[i];
      const piece = board[move.from_y]?.[move.from_x];
      if (piece) { board[move.from_y][move.from_x] = null; board[move.to_y][move.to_x] = piece; last = move; }
    }
    this.boardView.render(board, last ? { from_x: last.from_x, from_y: last.from_y, to_x: last.to_x, to_y: last.to_y } : undefined);
    const item = this.stepIndex ? this.replayList[this.stepIndex - 1] : null;
    if (this.roundEl) this.roundEl.textContent = String(item?.round ?? this.stepIndex);
    if (this.playerEl) this.playerEl.textContent = item ? (item.player === 0 ? 'Player 0 (Xanh dương)' : 'Player 1 (Đỏ)') : 'Bắt đầu';
    if (this.timeEl) this.timeEl.textContent = (item?.elapsed_ms ?? 0) + 'ms';
    const seek = document.getElementById('replay-seek');
    if (seek) { seek.max = String(this.replayList.length); seek.value = String(this.stepIndex); }
    this.updateReplayControls();
  }

  updateReplayControls() {
    const seek = document.getElementById('replay-seek');
    const toggle = document.getElementById('replay-toggle');
    if (seek) seek.disabled = !this.replayList?.length;
    if (toggle) toggle.textContent = this.paused ? '▶ Tiếp tục' : '⏸ Tạm dừng';
  }

  showResult(winnerSlot, reason) {
    this.resultBox.classList.remove('hidden');
    let winnerText = 'HÒA';
    if (winnerSlot === 0) winnerText = 'Player 0 (Xanh dương)';
    else if (winnerSlot === 1) winnerText = 'Player 1 (Đỏ)';

    this.resultTitle.textContent = `Người thắng: ${winnerText}`;
    this.resultDesc.textContent = `Lý do: ${reason || 'Trận đấu kết thúc'}`;
    const seed = document.getElementById('match-seed-result');
    if (seed) seed.textContent = `Map: ${this.replayData?.map_id || 'classic'}` + (this.replayData?.seed != null ? ` · Seed: ${this.replayData.seed}` : '');

    this.winAudio.play().catch(() => {});
  }
}
