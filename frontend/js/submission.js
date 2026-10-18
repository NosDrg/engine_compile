// frontend/js/submission.js
import { api } from './api.js';

export class SubmissionHandler {
  constructor() {
    this.initEvents();
  }

  initEvents() {
    document.getElementById('btn-validate-bot0')?.addEventListener('click', () => {
      this.handleValidate(0);
    });

    document.getElementById('btn-validate-bot1')?.addEventListener('click', () => {
      this.handleValidate(1);
    });
  }

  getBotData(playerIndex) {
    const idEl = document.getElementById(`bot${playerIndex}-id`);
    const langEl = document.getElementById(`bot${playerIndex}-lang`);
    const codeEl = document.getElementById(`bot${playerIndex}-code`);

    return {
      sub_id: idEl ? idEl.value.trim() : `bot_${playerIndex}`,
      lang_str: langEl ? langEl.value : 'python',
      code: codeEl ? codeEl.value : ''
    };
  }

  async handleValidate(playerIndex) {
    const statusEl = document.getElementById(`bot${playerIndex}-status`);
    const bot = this.getBotData(playerIndex);

    if (!statusEl) return;

    if (!bot.code.trim()) {
      statusEl.textContent = 'Vui lòng nhập code trước khi kiểm tra!';
      statusEl.className = 'status-msg error';
      return;
    }

    statusEl.textContent = 'Đang nộp và kiểm tra biên dịch...';
    statusEl.className = 'status-msg';

    try {
      // SỬA LỖI: api.validateCode nhận (sourceCode, language)
      const res = await api.validateCode(bot.code, bot.lang_str);
      if (res.success) {
        statusEl.textContent = res.message || 'Mã nguồn hợp lệ!';
        statusEl.className = 'status-msg success';
      } else {
        statusEl.textContent = res.error || res.message || 'Mã nguồn không hợp lệ.';
        statusEl.className = 'status-msg error';
      }
    } catch (err) {
      statusEl.textContent = err.message || 'Không thể kết nối máy chủ.';
      statusEl.className = 'status-msg error';
    }
  }
}