// frontend/js/board.js
export class BoardView {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.size = 9;
    this.cells = [];
    this.initGrid(); // Chỉ vẽ các ô khối rỗng lúc khởi tạo
  }

  /**
   * Chỉ vẽ 81 ô khối (block1.jpg, block2.jpg) và ô căn cứ A1, I9
   */
  initGrid() {
    this.container.innerHTML = '';
    this.cells = [];

    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const cell = document.createElement('div');
        const patternClass = (x + y) % 2 === 0 ? 'cell-light' : 'cell-dark';
        cell.className = `cell ${patternClass}`;
        cell.dataset.x = x;
        cell.dataset.y = y;

        // Đánh dấu căn cứ
        if (x === 0 && y === 0) cell.classList.add('goal-p1');
        if (x === 8 && y === 8) cell.classList.add('goal-p0');

        this.container.appendChild(cell);
        this.cells.push(cell);
      }
    }
  }

  /**
   * Xóa toàn bộ quân cờ, giữ lại các ô khối nền
   */
  clearPieces() {
    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const idx = y * this.size + x;
        const cell = this.cells[idx];
        if (!cell) continue;

        cell.innerHTML = '';
        const patternClass = (x + y) % 2 === 0 ? 'cell-light' : 'cell-dark';
        cell.className = `cell ${patternClass}`;

        if (x === 0 && y === 0) cell.classList.add('goal-p1');
        if (x === 8 && y === 8) cell.classList.add('goal-p0');
      }
    }
  }

  getPieceIcon(type) {
    if (!type) return '';
    const norm = String(type).toLowerCase();
    if (norm.includes('rock')) return 'assets/rock.png';
    if (norm.includes('paper')) return 'assets/paper.png';
    if (norm.includes('scissor')) return 'assets/scissors.png';
    return '';
  }

  /**
   * Kiểm tra nghiêm ngặt dữ liệu bàn cờ:
   * Phải là mảng 2 chiều 9x9 và có ít nhất 1 quân cờ thực sự
   */
  isValidBoardData(board) {
    if (!board || !Array.isArray(board) || board.length !== this.size) return false;
    let pieceCount = 0;
    for (let y = 0; y < this.size; y++) {
      if (!Array.isArray(board[y]) || board[y].length !== this.size) return false;
      for (let x = 0; x < this.size; x++) {
        if (board[y][x] && (board[y][x].piece_type || board[y][x].type)) {
          pieceCount++;
        }
      }
    }
    return pieceCount > 0;
  }

  /**
   * CHỈ vẽ quân cờ khi ĐỦ VÀ HỢP LỆ dữ liệu
   */
  render(board, lastMove = null) {
    // Nếu dữ liệu chưa đủ hoặc rỗng, chỉ xóa sạch quân, giữ nguyên nền bàn cờ
    if (!this.isValidBoardData(board)) {
      this.clearPieces();
      return;
    }

    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const idx = y * this.size + x;
        const cell = this.cells[idx];
        if (!cell) continue;

        cell.innerHTML = '';
        const patternClass = (x + y) % 2 === 0 ? 'cell-light' : 'cell-dark';
        cell.className = `cell ${patternClass}`;

        if (x === 0 && y === 0) cell.classList.add('goal-p1');
        if (x === 8 && y === 8) cell.classList.add('goal-p0');

        if (lastMove) {
          if (lastMove.from_x === x && lastMove.from_y === y) cell.classList.add('last-from');
          if (lastMove.to_x === x && lastMove.to_y === y) cell.classList.add('last-to');
        }

        const piece = board[y][x];
        if (piece) {
          const pieceEl = document.createElement('div');
          const owner = piece.owner !== undefined ? piece.owner : (piece.player !== undefined ? piece.player : 0);
          pieceEl.className = `piece owner-${owner}`;

          const pType = piece.piece_type || piece.type || piece.name;
          const iconSrc = this.getPieceIcon(pType);

          if (iconSrc) {
            const img = document.createElement('img');
            img.src = iconSrc;
            img.alt = pType;
            img.className = 'piece-img';
            pieceEl.appendChild(img);
          } else {
            pieceEl.textContent = pType ? pType[0] : '?';
          }

          cell.appendChild(pieceEl);
        }
      }
    }
  }
}