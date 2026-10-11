// js/app.js
import { BoardView } from './board.js';
import { SubmissionHandler } from './submission.js';
import { MatchController } from './match.js';

document.addEventListener('DOMContentLoaded', () => {
  // 1. Khởi tạo Bàn cờ
  const boardView = new BoardView('board-container');

  // 2. Khởi tạo Trình quản lý nộp bài
  const submissionHandler = new SubmissionHandler();

  // 3. Khởi tạo Bộ điều phối trận đấu
  const matchController = new MatchController(boardView);

  // 4. Lắng nghe nút Bắt đầu trận đấu
  document.getElementById('btn-start-match').addEventListener('click', async () => {
    const bot0 = submissionHandler.getBotData(0);
    const bot1 = submissionHandler.getBotData(1);

    if (!bot0.code || !bot1.code) {
      alert('Vui lòng nhập đầy đủ mã nguồn cho cả 2 Bot trước khi thi đấu!');
      return;
    }

    // Tự động kiểm tra nộp cả 2 bot trước khi bấm bắt đầu
    const v0 = await submissionHandler.handleValidate(0);
    const v1 = await submissionHandler.handleValidate(1);

    matchController.start(bot0, bot1);
  });
});