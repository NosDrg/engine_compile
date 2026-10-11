// js/board.js
export class BoardView {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.size = 9;
    this.cells = [];
    this.initGrid();
  }

  initGrid() {
    this.container.innerHTML = '';
    this.cells = [];

    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const cell = document.createElement('div');
        cell.className = 'cell';
        cell.dataset.x = x;
        cell.dataset.y = y;

        // Đánh dấu 2 ô mục tiêu căn cứ A1 và I9
        if (x === 0 && y === 0) cell.classList.add('goal-p1'); // Căn cứ A1
        if (x === 8 && y === 8) cell.classList.add('goal-p0'); // Căn cứ I9

        this.container.appendChild(cell);
        this.cells.push(cell);
      }
    }
  }

  getPieceIcon(type) {
    const iconMap = {
      'Rock': 'assets/icons/rock.png',
      'Paper': 'assets/icons/paper.png',
      'Scissors': 'assets/icons/scissors.png'
    };
    return iconMap[type] || '';
  }

  render(board, lastMove = null) {
    if (!board || board.length === 0) return;

    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const idx = y * this.size + x;
        const cell = this.cells[idx];
        cell.innerHTML = '';
        cell.className = 'cell';

        if (x === 0 && y === 0) cell.classList.add('goal-p1');
        if (x === 8 && y === 8) cell.classList.add('goal-p0');

        if (lastMove) {
          if (lastMove.from_x === x && lastMove.from_y === y) cell.classList.add('last-from');
          if (lastMove.to_x === x && lastMove.to_y === y) cell.classList.add('last-to');
        }

        const piece = board[y][x];
        if (piece) {
          const pieceEl = document.createElement('div');
          pieceEl.className = `piece owner-${piece.owner}`;
          
          const iconSrc = this.getPieceIcon(piece.piece_type);
          if (iconSrc) {
            const img = document.createElement('img');
            img.src = iconSrc;
            img.alt = piece.piece_type;
            img.className = 'piece-img';
            pieceEl.appendChild(img);
          } else {
            pieceEl.textContent = piece.piece_type[0];
          }

          cell.appendChild(pieceEl);
        }
      }
    }
  }
}