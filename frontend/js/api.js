// js/api.js
const API_BASE_URL = '/api';

export const api = {
  /**
   * Kiểm tra tính hợp lệ và cú pháp bot
   */
  async validateCode(username, sourceCode, language) {
    try {
      const response = await fetch(`${API_BASE_URL}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username,
          language: language,
          source_code: sourceCode
        })
      });
      const data = await response.json();
      if (!response.ok) {
        return { success: false, message: data.detail || 'Lỗi cú pháp' };
      }
      return { success: true, message: data.message };
    } catch (err) {
      return { success: false, message: `Lỗi kết nối Server: ${err.message}` };
    }
  },

  /**
   * Khởi động trận đấu
   */
  async createMatch(user0, user1) {
    try {
      const response = await fetch(`${API_BASE_URL}/duel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user0: user0,
          user1: user1
        })
      });
      const data = await response.json();
      if (!response.ok) {
        return { success: false, message: data.detail || 'Không thể tạo trận đấu' };
      }
      return data;
    } catch (err) {
      return { success: false, message: `Lỗi kết nối: ${err.message}` };
    }
  },

  /**
   * Lấy dữ liệu replay trận đấu từ SQLite
   */
  async getMatchState(matchId) {
    try {
      const response = await fetch(`${API_BASE_URL}/matches/${matchId}`);
      if (!response.ok) return null;
      return await response.json();
    } catch (err) {
      return null;
    }
  }
};