// frontend/js/api.js
const API_BASE_URL = '/api';

function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)arena_csrf=([^;]*)/);
  return match ? match[1] : '';
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set('Content-Type', 'application/json');
  if (options.method && !['GET', 'HEAD'].includes(options.method.toUpperCase())) {
    const token = csrfToken();
    if (token) headers.set('X-CSRF-Token', decodeURIComponent(token));
  }
  const response = await fetch(API_BASE_URL + path, { credentials: 'same-origin', ...options, headers });
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.error || 'Yêu cầu thất bại.');
  return data;
}

export const api = {
  me: () => request('/me'),
  publicProfile: (username) => request('/players/' + encodeURIComponent(username)),
  updateProfile: (payload) => request('/account/profile', { method: 'PATCH', body: JSON.stringify(payload) }),
  login: (username, password, remember = false) => request('/login', { method: 'POST', body: JSON.stringify({ username, password, remember }) }),
  register: (payload) => request('/register', { method: 'POST', body: JSON.stringify(payload) }),
  logout: () => request('/logout', { method: 'POST' }),
  changePassword: (current_password, new_password) => request('/account/password', { method: 'POST', body: JSON.stringify({ current_password, new_password }) }),
  validateCode: (sourceCode, language) => request('/validate', { method: 'POST', body: JSON.stringify({ source_code: sourceCode, language }) }),
  submitCode: (sourceCode, language, versionName) => request('/submissions', { method: 'POST', body: JSON.stringify({ source_code: sourceCode, language, version_name: versionName }) }),
  getSubmissions: () => request('/submissions'),
  activateSubmission: (id) => request('/submissions/' + encodeURIComponent(id) + '/activate', { method: 'POST' }),
  getOpponents: (excludeUser = '') => request('/opponents' + (excludeUser ? '?exclude=' + encodeURIComponent(excludeUser) : '')),
  createMatch: (user0, user1, ranked = false, seed = null, map_id = 'classic') => request('/queue', { method: 'POST', body: JSON.stringify({ user1, ranked, seed, map_id }) }),
  getQueueJob: (jobId) => request('/queue/' + encodeURIComponent(jobId)),
  cancelQueueJob: (jobId) => request('/queue/' + encodeURIComponent(jobId), { method: 'DELETE' }),
  getMatches: () => request('/matches'),
  getMatchState: (matchId) => request('/matches/' + encodeURIComponent(matchId)),
  getLeaderboard: () => request('/leaderboard'),
  getStats: () => request('/stats'),
  getTeam: () => request('/teams/me'),
  createTeam: (name) => request('/teams', { method: 'POST', body: JSON.stringify({ name }) }),
  joinTeam: (join_code) => request('/teams/join', { method: 'POST', body: JSON.stringify({ join_code }) }),
  leaveTeam: () => request('/teams/leave', { method: 'POST' }),
  rotateTeamCode: () => request('/teams/rotate-code', { method: 'POST' }),
  setTeamMemberRole: (id, role) => request('/teams/members/' + id, { method: 'PATCH', body: JSON.stringify({ role }) }),
  setTeamContestant: (memberId) => request('/teams/contestant', { method: 'PATCH', body: JSON.stringify({ member_id: memberId }) }),
  removeTeamMember: (id) => request('/teams/members/' + id, { method: 'DELETE' }),
  getTournaments: () => request('/tournaments'),
  getTournament: (id) => request('/tournaments/' + encodeURIComponent(id)),
  joinTournament: (id) => request('/tournaments/' + encodeURIComponent(id) + '/join', { method: 'POST' }),
  adminOverview: () => request('/admin/overview'),
  adminUsers: () => request('/admin/users'),
  setRole: (id, role) => request('/admin/users/' + id + '/role', { method: 'PATCH', body: JSON.stringify({ role }) }),
  resetUserPassword: (id, password) => request('/admin/users/' + id + '/password', { method: 'PUT', body: JSON.stringify({ password }) }),
  deleteUser: (id) => request('/admin/users/' + id, { method: 'DELETE' }),
  adminSubmissions: () => request('/admin/submissions'),
  adminForumMessages: () => request('/admin/forum/messages'),
  adminDeleteForumMessage: (id) => request('/admin/forum/messages/' + id, { method: 'DELETE' }),
  deleteSubmission: (id) => request('/admin/submissions/' + encodeURIComponent(id), { method: 'DELETE' }),
  adminSystem: () => request('/admin/system'),
  dailyMissions: () => request('/missions/daily'),
  pointsHistory: () => request('/missions/history'),
  checkIn: () => request('/missions/check-in', { method: 'POST' }),
  ratingHistory: () => request('/rating/history'),
  forumMessages: (before, after) => request('/forum/messages' + (after != null ? '?after=' + after : before != null ? '?before=' + before : '')),
  forumDeletions: (after) => request('/forum/deletions?after=' + after + '&limit=500'),
  notifications: () => request('/notifications'),
  markNotificationsRead: (notification_id = null) => request('/notifications/read', { method: 'PATCH', body: JSON.stringify({ notification_id }) }),
  createTournament: (payload) => request('/admin/tournaments', { method: 'POST', body: JSON.stringify(payload) }),
  startTournament: (id) => request('/admin/tournaments/' + encodeURIComponent(id) + '/start', { method: 'POST' }),
  retryTournamentGame: (tournamentId, gameId) => request('/admin/tournaments/' + encodeURIComponent(tournamentId) + '/games/' + encodeURIComponent(gameId) + '/retry', { method: 'POST' }),
};