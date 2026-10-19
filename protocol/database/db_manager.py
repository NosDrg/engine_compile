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
        """Khởi tạo toàn bộ cấu trúc bảng nếu database mới được tạo."""
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

            # 5. Bảng điểm thưởng và nhiệm vụ (user_points & mission_history)
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

            # 6. Bảng diễn đàn (forum_messages & forum_deletions)
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

            # Tạo sẵn tài khoản admin mặc định nếu chưa có
            admin_row = cursor.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
            if not admin_row:
                # password mặc định: admin123 (sha256)
                default_hash = hashlib.sha256("admin123".encode()).hexdigest()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, display_name, role)
                    VALUES ('admin', ?, 'Administrator', 'admin')
                """, (default_hash,))

            conn.commit()

    def get_or_create_user(self, username: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if row:
                return row["id"]
            cursor.execute("INSERT INTO users (username, display_name) VALUES (?, ?)", (username, username))
            conn.commit()
            return cursor.lastrowid