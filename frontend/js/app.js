// frontend/js/app.js
import { BoardView } from './board.js';
import { MatchController } from './match.js';
import { api } from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
  const boardView = new BoardView('board-container');
  const matchController = new MatchController(boardView);

  const myIdInput = document.getElementById('my-bot-id');
  const myLangSelect = document.getElementById('my-bot-lang');
  const myCodeText = document.getElementById('my-bot-code');
  const myStatus = document.getElementById('my-bot-status');
  const opponentSelect = document.getElementById('select-opponent');

  // Hàm tải danh sách đối thủ từ DB
  async function loadOpponents() {
    if (!opponentSelect) return;
    opponentSelect.innerHTML = '<option value="">Đang tải...</option>';
    const currentUsername = myIdInput.value.trim();
    const res = await api.getOpponents(currentUsername);

    opponentSelect.innerHTML = '';
    if (res.success && res.opponents && res.opponents.length > 0) {
      res.opponents.forEach(op => {
        const opt = document.createElement('option');
        opt.value = op.username;
        opt.textContent = `${op.username} (${op.language ? op.language.toUpperCase() : 'BOT'})`;
        opponentSelect.appendChild(opt);
      });
    } else {
      opponentSelect.innerHTML = '<option value="">(Chưa có đối thủ nào khác)</option>';
    }
  }

  // Tải danh sách ngay khi mở trang
  await loadOpponents();

  // Nút làm mới danh sách
  const refreshBtn = document.getElementById('btn-refresh-opponents');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadOpponents);
  }

  // Nút kiểm tra code
  const validateBtn = document.getElementById('btn-validate-my-bot');
  if (validateBtn) {
    validateBtn.addEventListener('click', async () => {
      const username = myIdInput.value.trim();
      const code = myCodeText.value;
      const lang = myLangSelect.value;

      if (!code.trim()) {
        myStatus.textContent = 'Vui lòng nhập mã nguồn trước khi kiểm tra!';
        myStatus.className = 'status-msg error';
        return;
      }

      myStatus.textContent = 'Đang kiểm tra cú pháp...';
      myStatus.className = 'status-msg';
      validateBtn.disabled = true;

      try {
        const res = await api.validateCode(username || 'test_user', code, lang);
        if (res.success) {
          myStatus.textContent = '✓ ' + (res.message || 'Mã nguồn hợp lệ!');
          myStatus.className = 'status-msg success';
        } else {
          myStatus.textContent = `✗ ${res.message}`;
          myStatus.className = 'status-msg error';
        }
      } finally {
        validateBtn.disabled = false;
      }
    });
  }

  // Nút nộp bot vào Database
  const submitBtn = document.getElementById('btn-submit-my-bot');
  if (submitBtn) {
    submitBtn.addEventListener('click', async () => {
      const username = myIdInput.value.trim();
      const code = myCodeText.value;
      const lang = myLangSelect.value;

      if (!username || !code.trim()) {
        myStatus.textContent = 'Vui lòng nhập tên thí sinh và mã nguồn!';
        myStatus.className = 'status-msg error';
        return;
      }

      myStatus.textContent = 'Đang kiểm tra và lưu vào Database...';
      myStatus.className = 'status-msg';
      submitBtn.disabled = true;

      try {
        const res = await api.validateCode(username, code, lang);
        if (res.success) {
          myStatus.textContent = '✓ Nộp bài thành công và đã lưu vào DB!';
          myStatus.className = 'status-msg success';
          await loadOpponents();
        } else {
          myStatus.textContent = `✗ Lỗi nộp bài: ${res.message}`;
          myStatus.className = 'status-msg error';
        }
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  // Nút Bắt đầu thách đấu
  const startMatchBtn = document.getElementById('btn-start-match');
  if (startMatchBtn) {
    startMatchBtn.addEventListener('click', async () => {
      const myUsername = myIdInput.value.trim();
      const opponentUsername = opponentSelect.value;
      const code = myCodeText.value;
      const lang = myLangSelect.value;

      if (!opponentUsername) {
        alert('Vui lòng chọn một đối thủ từ danh sách!');
        return;
      }

      if (code.trim()) {
        const submitRes = await api.validateCode(myUsername, code, lang);
        if (!submitRes.success) {
          alert(`Mã nguồn của bạn gặp lỗi: ${submitRes.message}`);
          return;
        }
      }

      matchController.start({ sub_id: myUsername }, { sub_id: opponentUsername });
    });
  }
});