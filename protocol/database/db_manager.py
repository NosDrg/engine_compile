# protocol/database/db_manager.py
import os
import sqlite3
import hashlib
import json
from typing import Optional, Dict, Any, List

class DatabaseManager:
    def __init__(self, db_path: str = "save/match_arena.db"):
        self.db_path = os.path.abspath(db_path)
        
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    language TEXT NOT NULL,
                    source_code TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_log TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY,
                    user0_id INTEGER NOT NULL,
                    sub0_id TEXT NOT NULL,
                    user1_id INTEGER NOT NULL,
                    sub1_id TEXT NOT NULL,
                    winner_user_id INTEGER,
                    reason TEXT NOT NULL,
                    bot0_ram_mb REAL,
                    bot1_ram_mb REAL,
                    replay_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user0_id) REFERENCES users(id),
                    FOREIGN KEY (user1_id) REFERENCES users(id),
                    FOREIGN KEY (sub0_id) REFERENCES submissions(id),
                    FOREIGN KEY (sub1_id) REFERENCES submissions(id)
                )
            """)
            conn.commit()

    @staticmethod
    def compute_hash(source_code: str) -> str:
        return hashlib.sha256(source_code.strip().encode("utf-8")).hexdigest()

    def get_or_create_user(self, username: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return row["id"]
            cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
            conn.commit()
            return cursor.lastrowid

    def save_submission(self, sub_id: str, user_id: int, language: str, source_code: str, status: str, error_log: str = "") -> None:
        code_hash = self.compute_hash(source_code)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO submissions (id, user_id, language, source_code, code_hash, status, error_log)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sub_id, user_id, language, source_code, code_hash, status, error_log))
            conn.commit()

    def get_latest_valid_submission(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM submissions 
                WHERE user_id = ? AND status = 'VALID' 
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_valid_opponents(self, exclude_username: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT u.username, s.id, s.language, s.created_at
            FROM submissions s
            JOIN users u ON s.user_id = u.id
            WHERE s.status = 'VALID'
            GROUP BY u.id
            ORDER BY s.created_at DESC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query).fetchall()

        opponents = []
        for r in rows:
            if exclude_username and r["username"] == exclude_username:
                continue
            opponents.append({
                "username": r["username"],
                "sub_id": r["id"],
                "language": r["language"]
            })
        return opponents

    def save_match(self, match_id: str, user0_id: int, sub0_id: str, user1_id: int, sub1_id: str,
                   winner_user_id: Optional[int], reason: str, bot0_ram: float, bot1_ram: float, replay_data: list) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO matches (
                    id, user0_id, sub0_id, user1_id, sub1_id,
                    winner_user_id, reason, bot0_ram_mb, bot1_ram_mb, replay_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id, user0_id, sub0_id, user1_id, sub1_id,
                winner_user_id, reason, bot0_ram, bot1_ram, json.dumps(replay_data)
            ))
            conn.commit()

    def get_match_by_id(self, match_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.*, 
                       u0.username as user0_name, s0.language as user0_lang,
                       u1.username as user1_name, s1.language as user1_lang,
                       uw.username as winner_name
                FROM matches m
                JOIN users u0 ON m.user0_id = u0.id
                JOIN submissions s0 ON m.sub0_id = s0.id
                JOIN users u1 ON m.user1_id = u1.id
                JOIN submissions s1 ON m.sub1_id = s1.id
                LEFT JOIN users uw ON m.winner_user_id = uw.id
                WHERE m.id = ?
            """, (match_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["replay_data"] = json.loads(data["replay_json"])
            del data["replay_json"]
            return data