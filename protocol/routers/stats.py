# protocol/routers/stats.py
from fastapi import APIRouter, Request
from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH

router = APIRouter(prefix="/api", tags=["Stats"])
db = DatabaseManager(DEFAULT_DB_PATH)

@router.get("/stats")
def get_stats():
    with db._get_connection() as conn:
        cursor = conn.cursor()
        players_cnt = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        matches_cnt = cursor.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    return {
        "success": True,
        "stats": {
            "players": players_cnt,
            "matches": matches_cnt
        }
    }

@router.get("/leaderboard")
def get_leaderboard():
    opponents = db.get_all_valid_opponents()
    leaderboard = []
    for op in opponents:
        leaderboard.append({
            "username": op["username"],
            "display_name": op["username"],
            "language": op["language"],
            "rating": 1000,
            "wins": 0,
            "losses": 0,
            "draws": 0
        })
    return {"success": True, "leaderboard": leaderboard}

@router.get("/rating/history")
def get_rating_history(request: Request):
    username = request.cookies.get("arena_user")
    if not username:
        return {"success": True, "events": []}

    user_id = db.get_or_create_user(username)
    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT old_rating, new_rating, created_at
            FROM rating_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
        """, (user_id,)).fetchall()

    return {
        "success": True,
        "events": [dict(r) for r in rows]
    }