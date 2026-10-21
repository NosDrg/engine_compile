# protocol/routers/forum.py
import json
import jwt
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Query

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH
from routers.auth import JWT_SECRET, JWT_ALGORITHM  # <-- THÊM MỚI

router = APIRouter(prefix="/api/forum", tags=["Forum"])
db = DatabaseManager(DEFAULT_DB_PATH)

# Đảm bảo bảng lưu tin nhắn diễn đàn tồn tại
with db._get_connection() as conn:
    cursor = conn.cursor()
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
    conn.commit()

# Quản lý danh sách kết nối WebSocket đang hoạt động
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data))
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)

manager = ConnectionManager()

# --- REST Endpoints cho Polling và Lịch sử ---
@router.get("/messages")
def get_forum_messages(before: Optional[int] = None, after: Optional[int] = None):
    query = "SELECT id, username, display_name, body, created_at FROM forum_messages"
    params = []
    
    if after is not None and after > 0:
        query += " WHERE id > ? ORDER BY id ASC"
        params.append(after)
    elif before is not None:
        query += " WHERE id < ? ORDER BY id DESC LIMIT 50"
        params.append(before)
    else:
        query += " ORDER BY id DESC LIMIT 50"

    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(query, params).fetchall()

    messages = [dict(r) for r in rows]
    if before is None and (after is None or after == 0):
        messages.reverse()

    return {"messages": messages}

@router.get("/deletions")
def get_forum_deletions(after: int = 0, limit: int = 500):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT id, message_id FROM forum_deletions WHERE id > ? ORDER BY id ASC LIMIT ?",
            (after, limit)
        ).fetchall()
    return {"deletions": [dict(r) for r in rows]}

@router.websocket("/ws")
async def forum_websocket_endpoint(websocket: WebSocket):
    token = websocket.cookies.get("arena_token") or websocket.query_params.get("token")
    username = "Guest"
    display_name = "Guest"

    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            uname = payload.get("sub")
            if uname:
                user = db.get_user_by_username(uname)
                if user:
                    username = user["username"]
                    display_name = user.get("display_name") or username
        except Exception:
            pass

    await manager.connect(websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError:
                continue

            body = payload.get("body", "").strip()
            if not body:
                continue

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Lưu vào SQLite
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO forum_messages (username, display_name, body, created_at) VALUES (?, ?, ?, ?)",
                    (username, display_name, body, created_at)
                )
                conn.commit()
                message_id = cursor.lastrowid

            msg_data = {
                "type": "message",
                "message": {
                    "id": message_id,
                    "username": username,
                    "display_name": display_name,
                    "body": body,
                    "created_at": created_at
                }
            }
            # Gửi tin nhắn tức thì đến tất cả client đang online
            await manager.broadcast(msg_data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)