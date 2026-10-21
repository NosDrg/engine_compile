// frontend/js/replay_controller.js
export class ReplayController {
  constructor({ onRenderTurn, onMatchEnd }) {
    this.moves = [];
    this.currentTurn = 0;
    this.timer = null;
    this.speedMs = 600;
    this.onRenderTurn = onRenderTurn;
    this.onMatchEnd = onMatchEnd;

    // DOM Elements
    this.slider = document.getElementById('replay-slider');
    this.lblCurrent = document.getElementById('turn-current-label');
    this.lblMax = document.getElementById('turn-max-label');
    this.btnPlay = document.getElementById('btn-play-pause');
    this.btnPrev = document.getElementById('btn-prev-turn');
    this.btnNext = document.getElementById('btn-next-turn');
    this.speedSelect = document.getElementById('playback-speed');
    this.statusBox = document.getElementById('move-status-box');

    this._bindEvents();
  }

  _bindEvents() {
    this.btnPlay.addEventListener('click', () => this.togglePlay());
    this.btnPrev.addEventListener('click', () => this.step(-1));
    this.btnNext.addEventListener('click', () => this.step(1));

    this.slider.addEventListener('input', (e) => {
      this.pause();
      this.goToTurn(parseInt(e.target.value, 10));
    });

    this.speedSelect.addEventListener('change', (e) => {
      this.speedMs = parseInt(e.target.value, 10);
      if (this.isPlaying()) {
        this.pause();
        this.play();
      }
    });
  }

  loadMatch(moveHistory, initialStatus = "Bắt đầu ván đấu") {
    this.pause();
    this.moves = Array.isArray(moveHistory) ? moveHistory : [];
    this.currentTurn = 0;

    const total = this.moves.length;
    this.slider.max = total;
    this.slider.value = 0;
    this.slider.disabled = total === 0;
    this.btnPlay.disabled = total === 0;
    this.btnPrev.disabled = total === 0;
    this.btnNext.disabled = total === 0;

    this.lblMax.textContent = `/ ${total}`;
    this.lblCurrent.textContent = `Lượt: 0`;
    this.statusBox.textContent = initialStatus;

    if (this.onRenderTurn) {
      this.onRenderTurn(null, 0);
    }
  }

  isPlaying() {
    return this.timer !== null;
  }

  play() {
    if (this.isPlaying() || this.moves.length === 0) return;
    if (this.currentTurn >= this.moves.length) {
      this.currentTurn = 0;
    }
    this.btnPlay.textContent = '⏸ Tạm dừng';
    this.timer = setInterval(() => {
      if (this.currentTurn < this.moves.length) {
        this.step(1);
      } else {
        this.pause();
        if (this.onMatchEnd) this.onMatchEnd();
      }
    }, this.speedMs);
  }

  pause() {
    if (!this.isPlaying()) return;
    clearInterval(this.timer);
    this.timer = null;
    this.btnPlay.textContent = '▶ Tiếp tục';
  }

  togglePlay() {
    this.isPlaying() ? this.pause() : this.play();
  }

  step(delta) {
    const nextTurn = this.currentTurn + delta;
    if (nextTurn >= 0 && nextTurn <= this.moves.length) {
      this.goToTurn(nextTurn);
    }
  }

  goToTurn(turnIndex) {
    this.currentTurn = turnIndex;
    this.slider.value = turnIndex;
    this.lblCurrent.textContent = `Lượt: ${turnIndex}`;

    const currentMove = turnIndex > 0 ? this.moves[turnIndex - 1] : null;
    if (currentMove) {
      const player = currentMove.player ?? (turnIndex % 2 === 1 ? 0 : 1);
      this.statusBox.textContent = `Lượt ${turnIndex} [Player ${player}]: ${JSON.stringify(currentMove.action || currentMove)}`;
    } else {
      this.statusBox.textContent = "Bàn cờ ban đầu.";
    }

    if (this.onRenderTurn) {
      this.onRenderTurn(currentMove, turnIndex);
    }
  }
}