// frontend/js/match.js
import { api } from './api.js';

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
    if (this.resultBox) this.resultBox.classList.add('hidden');

    if (this.roundEl) this.roundEl.textContent = '0';
    if (this.playerEl) this.playerEl.textContent = 'Đang tải trận đấu...';
    if (this.timeEl) this.timeEl.textContent = '0ms';

    let res;
    const currentRunId = Symbol('run_token');
    this._currentRunToken = currentRunId;

    try {
      const queued = await api.createMatch(
        bot0.sub_id,
        bot1.sub_id,
        Boolean(bot0.ranked),
        bot0.seed ?? null,
        bot0.map_id ?? 'classic'
      );

      if (!queued || !queued.job_id) {
        throw new Error(queued?.error || 'Không tạo được lượt đấu.');
      }

      this.activeJobId = queued.job_id;
      const cancelButton = document.getElementById('btn-cancel-match');
      if (cancelButton) {
        cancelButton.hidden = false;
        cancelButton.disabled = false;
        cancelButton.textContent = 'Hủy trận đang chờ';
      }

      if (this.playerEl) this.playerEl.textContent = 'Đang chờ engine…';

      // Polling vòng lặp có bảo vệ Race Condition
      for (let attempt = 0; attempt < 900; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Nếu trận đã bị hủy bởi lượt bấm mới
        if (this._currentRunToken !== currentRunId) return;

        let status;
        try {
          status = await api.getQueueJob(queued.job_id);
        } catch {
          continue; // Bỏ qua 1 nhịp chập chờn mạng, không quăng lỗi ngay
        }

        if (!status || !status.job) continue;

        if (status.job.status === 'cancelled') {
          if (this.playerEl) this.playerEl.textContent = 'Trận đã được hủy';
          this.activeJobId = null;
          if (cancelButton) cancelButton.hidden = true;
          return;
        }

        if (cancelButton) {
          const isQueued = status.job.status === 'queued';
          cancelButton.hidden = !isQueued;
          cancelButton.disabled = !isQueued;
        }

        if (status.job.status === 'failed') {
          throw new Error(status.job.error_text || status.job.result?.error || 'Trận đấu thất bại.');
        }

        if (status.job.status === 'completed') {
          res = status.job.result;
          break;
        }

        if (this.playerEl) {
          this.playerEl.textContent = status.job.status === 'running' ? 'Đang chạy trận…' : 'Đang chờ engine…';
        }
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
    try {
      const result = await api.cancelQueueJob(this.activeJobId);
      const isOk = result?.status === 'cancelled';
      if (isOk) this.activeJobId = null;
      return isOk;
    } catch {
      return false;
    }
  }

  playReplay(res) {
    this.stopPlayback();
    if (this.resultBox) this.resultBox.classList.add('hidden');

    const replayList = res.replay || [];
    let initialBoard = res.initial_board || res.board;

    // Phục hồi bàn cờ nếu thiếu dữ liệu, chống alert chặn người dùng
    if (!initialBoard || !Array.isArray(initialBoard)) {
      console.warn("initial_board rỗng, tự động tạo ma trận 9x9 trống");
      initialBoard = Array.from({ length: 9 }, () => Array(9).fill(null));
    }

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
    }, Math.max(50, 700 / (this.playbackSpeed || 1)));
  }

  renderReplayStep(step) {
    this.stepIndex = Math.max(0, Math.min(step, this.replayList.length));
    const board = JSON.parse(JSON.stringify(this.initialBoard));
    let last = null;

    for (let i = 0; i < this.stepIndex; i++) {
      const move = this.replayList[i].move_obj || this.replayList[i].move || this.replayList[i];
      if (!move) continue;

      const fx = Number(move.from_x), fy = Number(move.from_y);
      const tx = Number(move.to_x), ty = Number(move.to_y);

      // Kiểm tra an toàn biên mảng để tránh TypeError
      if (board[fy] && board[fy][fx] && board[ty]) {
        const piece = board[fy][fx];
        board[fy][fx] = null;
        board[ty][tx] = piece;
        last = { from_x: fx, from_y: fy, to_x: tx, to_y: ty };
      }
    }

    this.boardView.render(board, last || undefined);

    const item = this.stepIndex ? this.replayList[this.stepIndex - 1] : null;
    if (this.roundEl) this.roundEl.textContent = String(item?.round ?? this.stepIndex);
    if (this.playerEl) {
      const p = item ? (item.player !== undefined ? item.player : item.player_id) : null;
      this.playerEl.textContent = p !== null ? (p === 0 ? 'Player 0 (Xanh dương)' : 'Player 1 (Đỏ)') : 'Bắt đầu';
    }
    if (this.timeEl) this.timeEl.textContent = `${item?.elapsed_ms ?? item?.execution_time_ms ?? 0}ms`;

    const seek = document.getElementById('replay-seek');
    if (seek) {
      seek.max = String(this.replayList.length);
      seek.value = String(this.stepIndex);
    }
    this.updateReplayControls();
  }

  updateReplayControls() {
    const seek = document.getElementById('replay-seek');
    const toggle = document.getElementById('replay-toggle');
    if (seek) seek.disabled = !this.replayList?.length;
    if (toggle) toggle.textContent = this.paused ? '▶ Tiếp tục' : '⏸ Tạm dừng';
  }

  showResult(winnerSlot, reason) {
    if (!this.resultBox) return;
    this.resultBox.classList.remove('hidden');

    let winnerText = 'HÒA';
    if (winnerSlot === 0) winnerText = 'Player 0 (Xanh dương)';
    else if (winnerSlot === 1) winnerText = 'Player 1 (Đỏ)';

    if (this.resultTitle) this.resultTitle.textContent = `Người thắng: ${winnerText}`;
    if (this.resultDesc) this.resultDesc.textContent = `Lý do: ${reason || 'Trận đấu kết thúc'}`;

    const seed = document.getElementById('match-seed-result');
    if (seed) {
      seed.textContent = `Map: ${this.replayData?.map_id || 'classic'}` + 
        (this.replayData?.seed != null ? ` · Seed: ${this.replayData.seed}` : '');
    }

    this.winAudio.play().catch(() => {});
  }
}