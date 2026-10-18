// js/submission.js
import { api } from './api.js';

export class SubmissionHandler {
  constructor() {
    this.initEvents();
  }

  initEvents() {
    document.getElementById('btn-validate-bot0').addEventListener('click', () => {
      this.handleValidate(0);
    });

    document.getElementById('btn-validate-bot1').addEventListener('click', () => {
      this.handleValidate(1);
    });
  }

  getBotData(playerIndex) {
    return {
      sub_id: document.getElementById(`bot${playerIndex}-id`).value.trim(),
      lang_str: document.getElementById(`bot${playerIndex}-lang`).value,
      code: document.getElementById(`bot${playerIndex}-code`).value
    };
  }

  async handleValidate(playerIndex) {
    const statusEl = document.getElementById(`bot${playerIndex}-status`);
    const bot = this.getBotData(playerIndex);

    if (!bot.code) {
      statusEl.textContent = 'Vui lòng nhập code trước khi kiểm tra!';
      statusEl.className = 'status-msg error';
      return;
    }

    statusEl.textContent = 'Đang nộp và kiểm tra biên dịch...';
    statusEl.className = 'status-msg';

    const res = await api.validateCode(bot.sub_id, bot.code, bot.lang_str);
    if (res.success) {
      statusEl.textContent = '✓ ' + (res.message || 'Mã nguồn hợp lệ!');
      statusEl.className = 'status-msg success';
    } else {
      statusEl.textContent = `✗ ${res.message}`;
      statusEl.className = 'status-msg error';
    }
  }
}