# protocol/database/db_manager.py
import os
import sqlite3
import hashlib
import json
from typing import Optional, Dict, Any, List

class DatabaseManager:
    def __init__(self, db_path: str = "save/match_arena.db"):
        self.db_path = os.path.abspath(db_path)
        
        # Đảm bảo thư mục chứa file db luôn tồn tại
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Khởi tạo toàn bộ cấu trúc bảng và tự động migrate các cột còn thiếu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Bảng người dùng (users)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    display_name TEXT,
                    role TEXT DEFAULT 'player',
                    avatar_id TEXT DEFAULT 'robot',
                    bio TEXT DEFAULT '',
                    rating INTEGER DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # TỰ ĐỘNG MIGRATION: Bổ sung các cột nếu bảng users cũ bị thiếu
            cursor.execute("PRAGMA table_info(users)")
            existing_columns = {row["name"] for row in cursor.fetchall()}
            
            missing_columns = {
                "password_hash": "TEXT",
                "display_name": "TEXT",
                "role": "TEXT DEFAULT 'player'",
                "avatar_id": "TEXT DEFAULT 'robot'",
                "bio": "TEXT DEFAULT ''",
                "rating": "INTEGER DEFAULT 1000"
            }
            for col_name, col_def in missing_columns.items():
                if col_name not in existing_columns:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")

            # 2. Bảng mã nguồn bot (submissions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    language TEXT NOT NULL,
                    source_code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_log TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # 3. Bảng lịch sử trận đấu (matches)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY,
                    user0_id INTEGER NOT NULL,
                    user1_id INTEGER NOT NULL,
                    winner_user_id INTEGER,
                    user0_lang TEXT,
                    user1_lang TEXT,
                    bot0_ram_mb REAL,
                    bot1_ram_mb REAL,
                    reason TEXT,
                    replay_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user0_id) REFERENCES users(id),
                    FOREIGN KEY (user1_id) REFERENCES users(id)
                )
            """)

            # 4. Bảng lịch sử điểm xếp hạng (rating_history)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rating_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    old_rating INTEGER NOT NULL,
                    new_rating INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # 5. Bảng điểm thưởng và nhiệm vụ
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    user_id INTEGER PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    last_check_in DATE,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mission_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    mission_key TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # 6. Bảng diễn đàn
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forum_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    body TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forum_deletions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. Bảng môi trường thực thi (runtimes)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS runtimes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    compile_cmd TEXT,
                    run_cmd TEXT NOT NULL,
                    timeout_sec REAL DEFAULT 2.0,
                    memory_limit_mb INTEGER DEFAULT 128,
                    is_enabled INTEGER DEFAULT 1
                )
            ''')

            runtime_count = cursor.execute('SELECT COUNT(*) FROM runtimes').fetchone()[0]
            if runtime_count == 0:
                cursor.executemany('''
                    INSERT INTO runtimes (id, name, extension, compile_cmd, run_cmd, timeout_sec, memory_limit_mb, is_enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    ('python', 'Python 3.11', 'py', '', 'python {source}', 2.0, 128, 1),
                    ('cpp', 'C++ (GCC)', 'cpp', 'g++ -O3 {source} -o {bin}', '{bin}', 2.0, 128, 1)
                ])

            # 8. Bảng trò chơi động (games)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    slug TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    board_type TEXT DEFAULT 'grid_9x9',
                    referee_code TEXT,
                    starter_bot_code TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            game_count = cursor.execute('SELECT COUNT(*) FROM games').fetchone()[0]
            if game_count == 0:
                default_referee_code = '''# referee.py - Default Caro 9x9 Referee
def init_game() -> dict:
    return {
        "board": [[None for _ in range(9)] for _ in range(9)],
        "turn": 0,
        "max_turns": 81
    }

def validate_move(state: dict, move: dict, player_slot: int) -> bool:
    if not isinstance(move, dict):
        return False
    row = move.get("row")
    col = move.get("col")
    if row is None or col is None:
        return False
    if not isinstance(row, int) or not isinstance(col, int):
        return False
    if not (0 <= row < 9 and 0 <= col < 9):
        return False
    board = state.get("board", [])
    if row >= len(board) or col >= len(board[row]):
        return False
    return board[row][col] is None

def apply_move(state: dict, move: dict, player_slot: int) -> tuple:
    import copy
    new_state = copy.deepcopy(state)
    r = int(move["row"])
    c = int(move["col"])
    new_state["board"][r][c] = player_slot
    new_state["turn"] = int(new_state.get("turn", 0)) + 1
    
    board = new_state["board"]
    size = len(board)
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    for dr, dc in directions:
        count = 1
        nr, nc = r + dr, c + dc
        while 0 <= nr < size and 0 <= nc < size and board[nr][nc] == player_slot:
            count += 1
            nr += dr
            nc += dc
        nr, nc = r - dr, c - dc
        while 0 <= nr < size and 0 <= nc < size and board[nr][nc] == player_slot:
            count += 1
            nr -= dr
            nc -= dc
        if count >= 5:
            return new_state, player_slot, f"Người chơi {player_slot} nối thành công 5 điểm liên tiếp!"

    if new_state["turn"] >= int(new_state.get("max_turns", 81)):
        return new_state, -1, "Hòa cờ - Đã hết lượt đi tối đa."

    return new_state, None, "Nước đi hợp lệ."
'''
                default_starter_code = '''import sys
import json
import random

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            state = json.loads(line.strip())
            board = state.get("board", [])
            empty_cells = []
            for r in range(len(board)):
                for c in range(len(board[r])):
                    if board[r][c] is None:
                        empty_cells.append({"row": r, "col": c})
            if empty_cells:
                move = random.choice(empty_cells)
                print(json.dumps(move), flush=True)
            else:
                print(json.dumps({"action": "PASS"}), flush=True)
        except Exception:
            print(json.dumps({"action": "PASS"}), flush=True)

if __name__ == "__main__":
    main()
'''
                cursor.execute('''
                    INSERT INTO games (slug, name, description, board_type, referee_code, starter_bot_code, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (
                    'default',
                    'Caro 9x9 Arena',
                    'Trận chiến thuật toán cờ caro 9x9 tiêu chuẩn',
                    'grid_9x9',
                    default_referee_code,
                    default_starter_code
                ))

            # Tạo tài khoản admin mặc định nếu chưa có
            admin_user = os.getenv("ADMIN_USERNAME", "admin")
            admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
            admin_hash = hashlib.sha256(admin_pass.encode()).hexdigest()

            admin_row = cursor.execute("SELECT id FROM users WHERE username = ?", (admin_user,)).fetchone()
            if not admin_row:
                cursor.execute("""
                    INSERT INTO users (username, password_hash, display_name, role)
                    VALUES (?, ?, 'Administrator', 'admin')
                """, (admin_user, admin_hash))

            conn.commit()

    def get_or_create_user(self, username: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if row:
                return row["id"]
            cursor.execute("INSERT INTO users (username, display_name) VALUES (?, ?)", (username, username))
            conn.commit()
            return cursor.lastrowid # type: ignore


    # protocol/database/db_manager.py
# (Bổ sung vào bên trong class DatabaseManager)

    def get_all_valid_opponents(self, exclude_username: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy danh sách các đối thủ có bot hợp lệ (VALID), sắp xếp theo rating giảm dần."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Lấy submission VALID mới nhất của từng user
            query = """
                SELECT u.id as user_id, u.username, 
                       COALESCE(u.display_name, u.username) as display_name,
                       COALESCE(u.rating, 1000) as rating,
                       s.language, s.id as submission_id
                FROM users u
                JOIN submissions s ON u.id = s.user_id
                WHERE s.status = 'VALID'
            """
            params = []
            if exclude_username:
                query += " AND u.username != ?"
                params.append(exclude_username)
            
            # Nhóm theo user và lấy bản nộp mới nhất
            query += " GROUP BY u.id ORDER BY u.rating DESC, s.created_at DESC"
            
            rows = cursor.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_match_by_id(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Lấy chi tiết và replay data của một trận đấu theo ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT m.*,
                       u0.username as user0_name,
                       u1.username as user1_name,
                       uw.username as winner_name
                FROM matches m
                JOIN users u0 ON m.user0_id = u0.id
                JOIN users u1 ON m.user1_id = u1.id
                LEFT JOIN users uw ON m.winner_user_id = uw.id
                WHERE m.id = ?
            """, (match_id,)).fetchone()
            
            if not row:
                return None
                
            data = dict(row)
            # Parse chuỗi JSON replay_data thành dict nếu cần
            if isinstance(data.get("replay_data"), str):
                try:
                    data["replay_data"] = json.loads(data["replay_data"])
                except Exception:
                    pass
            return data

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin người dùng theo username."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return dict(row) if row else None

    def verify_user_password(self, username: str, password_raw: str) -> bool:
        """Kiểm tra mật khẩu đăng nhập (SHA256)."""
        user = self.get_user_by_username(username)
        if not user or not user.get("password_hash"):
            return False
        input_hash = hashlib.sha256(password_raw.encode()).hexdigest()
        return user["password_hash"] == input_hash

    def update_user_rating(self, user_id: int, new_rating: int):
        """Cập nhật điểm ELO và ghi log vào rating_history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT rating FROM users WHERE id = ?", (user_id,)).fetchone()
            old_rating = row["rating"] if row else 1000
            
            cursor.execute("UPDATE users SET rating = ? WHERE id = ?", (new_rating, user_id))
            cursor.execute(
                "INSERT INTO rating_history (user_id, old_rating, new_rating) VALUES (?, ?, ?)",
                (user_id, old_rating, new_rating)
            )
            conn.commit()

    def save_submission(
        self, 
        sub_id: str, 
        user_id: int, 
        language: str, 
        source_code: str, 
        status: str = "VALID", 
        error_log: Optional[str] = None,
        **kwargs
    ):
        """Lưu bài nộp của thí sinh kèm log lỗi cú pháp nếu có."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO submissions (id, user_id, language, source_code, status, error_log)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sub_id, user_id, language, source_code, status, error_log))
            conn.commit()

    def update_submission_status(self, sub_id: str, status: str, error_log: Optional[str] = None):
        """Cập nhật trạng thái kiểm thử (VALID / INVALID / ERROR) của submission."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE submissions 
                SET status = ?, error_log = ?
                WHERE id = ?
            """, (status, error_log, sub_id))
            conn.commit()

    def get_latest_valid_submission(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Lấy phiên bản bot hợp lệ gần nhất của người chơi để đưa vào sàn đấu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT * FROM submissions 
                WHERE user_id = ? AND status = 'VALID' 
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,)).fetchone()
            return dict(row) if row else None

    def save_match(
        self,
        match_id: str,
        user0_id: int,
        user1_id: int,
        winner_user_id: Optional[int] = None,
        reason: str = "UNKNOWN",
        bot0_ram: float = 0.0,
        bot1_ram: float = 0.0,
        replay_data: Any = None,
        sub0_id: Optional[str] = None,
        sub1_id: Optional[str] = None,
        sub0_code_hash: Optional[str] = None,
        sub1_code_hash: Optional[str] = None,
        **kwargs
    ):
        """Lưu lịch sử trận đấu và replay."""
        import json
        replay_str = json.dumps(replay_data) if isinstance(replay_data, (list, dict)) else str(replay_data or "")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO matches (
                    id, user0_id, user1_id, winner_user_id, reason,
                    bot0_ram_mb, bot1_ram_mb, replay_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id, user0_id, user1_id, winner_user_id, reason,
                bot0_ram, bot1_ram, replay_str
            ))
            conn.commit()

    def get_active_games(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả game đang kích hoạt (is_active = 1)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute('''
                SELECT slug, name, description, board_type, starter_bot_code, is_active, created_at, updated_at
                FROM games
                WHERE is_active = 1
                ORDER BY created_at ASC
            ''').fetchall()
            return [dict(r) for r in rows]

    def get_all_games(self) -> List[Dict[str, Any]]:
        """Lấy toàn bộ danh sách game cho trang quản trị (Admin)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute('''
                SELECT slug, name, description, board_type, referee_code, starter_bot_code, is_active, created_at, updated_at
                FROM games
                ORDER BY created_at DESC
            ''').fetchall()
            return [dict(r) for r in rows]

    def get_game_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Lấy chi tiết 1 game bao gồm referee_code."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute('SELECT * FROM games WHERE slug = ?', (slug,)).fetchone()
            return dict(row) if row else None

    def upsert_game(self, data: Dict[str, Any]) -> None:
        """Chèn hoặc cập nhật game theo cú pháp ON CONFLICT(slug) DO UPDATE."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO games (slug, name, description, board_type, referee_code, starter_bot_code, is_active, created_at, updated_at)
                VALUES (:slug, :name, :description, :board_type, :referee_code, :starter_bot_code, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(slug) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    board_type = excluded.board_type,
                    referee_code = excluded.referee_code,
                    starter_bot_code = excluded.starter_bot_code,
                    is_active = excluded.is_active,
                    updated_at = CURRENT_TIMESTAMP
            ''', {
                'slug': data.get('slug'),
                'name': data.get('name'),
                'description': data.get('description', ''),
                'board_type': data.get('board_type', 'grid_9x9'),
                'referee_code': data.get('referee_code', ''),
                'starter_bot_code': data.get('starter_bot_code', ''),
                'is_active': 1 if data.get('is_active', 1) in (1, True, '1', 'true') else 0
            })
            conn.commit()

    def get_runtimes(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Lấy danh sách cấu hình runtimes/compilers."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM runtimes'
            if enabled_only:
                query += ' WHERE is_enabled = 1'
            query += ' ORDER BY id ASC'
            rows = cursor.execute(query).fetchall()
            return [dict(r) for r in rows]

    def get_runtime_by_id(self, runtime_id: str) -> Optional[Dict[str, Any]]:
        """Lấy cấu hình của một runtime theo id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute('SELECT * FROM runtimes WHERE id = ?', (runtime_id,)).fetchone()
            return dict(row) if row else None

    def upsert_runtime(self, data: Dict[str, Any]) -> None:
        """Chèn hoặc cập nhật runtime theo ON CONFLICT(id) DO UPDATE."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO runtimes (id, name, extension, compile_cmd, run_cmd, timeout_sec, memory_limit_mb, is_enabled)
                VALUES (:id, :name, :extension, :compile_cmd, :run_cmd, :timeout_sec, :memory_limit_mb, :is_enabled)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    extension = excluded.extension,
                    compile_cmd = excluded.compile_cmd,
                    run_cmd = excluded.run_cmd,
                    timeout_sec = excluded.timeout_sec,
                    memory_limit_mb = excluded.memory_limit_mb,
                    is_enabled = excluded.is_enabled
            ''', {
                'id': data.get('id'),
                'name': data.get('name'),
                'extension': data.get('extension', '').lstrip('.'),
                'compile_cmd': data.get('compile_cmd', ''),
                'run_cmd': data.get('run_cmd', ''),
                'timeout_sec': float(data.get('timeout_sec', 2.0)),
                'memory_limit_mb': int(data.get('memory_limit_mb', 128)),
                'is_enabled': 1 if data.get('is_enabled', 1) in (1, True, '1', 'true') else 0
            })
            conn.commit()
