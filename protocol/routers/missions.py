# protocol/routers/missions.py
from datetime import datetime
from fastapi import APIRouter, Request

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH

router = APIRouter(prefix="/api/missions", tags=["Missions"])
db = DatabaseManager(DEFAULT_DB_PATH)

# Khởi tạo bảng lưu điểm thưởng và lịch sử nhiệm vụ nếu chưa có
with db._get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_points (
            user_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            last_check_in DATE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mission_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mission_key TEXT NOT NULL,
            points INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

@router.get("/daily")
def get_daily_missions(request: Request):
    username = request.cookies.get("arena_user") or "anonymous"
    user_id = db.get_or_create_user(username)
    today_str = datetime.now().strftime("%Y-%m-%d")

    with db._get_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT points, last_check_in FROM user_points WHERE user_id = ?", (user_id,)).fetchone()
        
    points = row["points"] if row else 0
    checked_in = (row["last_check_in"] == today_str) if row else False

    # Danh sách nhiệm vụ hằng ngày
    missions = [
        {
            "key": "check_in",
            "title": "Điểm danh hàng ngày",
            "progress": 1 if checked_in else 0,
            "target": 1,
            "reward": 50,
            "done": checked_in
        },
        {
            "key": "play_matches",
            "title": "Tham gia 3 trận đấu",
            "progress": 0,
            "target": 3,
            "reward": 100,
            "done": False
        },
        {
            "key": "submit_bot",
            "title": "Nộp phiên bản bot mới",
            "progress": 0,
            "target": 1,
            "reward": 150,
            "done": False
        }
    ]

    return {
        "success": True,
        "points": points,
        "missions": missions
    }

@router.get("/history")
def get_points_history(request: Request):
    username = request.cookies.get("arena_user") or "anonymous"
    user_id = db.get_or_create_user(username)

    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT mission_key, points, created_at 
            FROM mission_history 
            WHERE user_id = ? 
            ORDER BY id DESC LIMIT 50
        """, (user_id,)).fetchall()

    return {
        "success": True,
        "history": [dict(r) for r in rows]
    }

@router.post("/check-in")
def check_in(request: Request):
    username = request.cookies.get("arena_user") or "anonymous"
    user_id = db.get_or_create_user(username)
    today_str = datetime.now().strftime("%Y-%m-%d")

    with db._get_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("SELECT points, last_check_in FROM user_points WHERE user_id = ?", (user_id,)).fetchone()
        
        if row and row["last_check_in"] == today_str:
            return {"success": True, "already_done": True, "message": "Hôm nay bạn đã điểm danh rồi."}

        reward = 50
        if not row:
            cursor.execute("INSERT INTO user_points (user_id, points, last_check_in) VALUES (?, ?, ?)",
                           (user_id, reward, today_str))
        else:
            cursor.execute("UPDATE user_points SET points = points + ?, last_check_in = ? WHERE user_id = ?",
                           (reward, today_str, user_id))

        cursor.execute("INSERT INTO mission_history (user_id, mission_key, points) VALUES (?, ?, ?)",
                       (user_id, "Điểm danh hàng ngày", reward))
        conn.commit()

    return {"success": True, "already_done": False, "points_earned": reward}