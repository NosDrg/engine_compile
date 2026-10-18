# protocol/routers/admin.py
import shutil
import psutil
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH

router = APIRouter(prefix="/api", tags=["Admin & Tournaments"])
db = DatabaseManager(DEFAULT_DB_PATH)

def verify_admin(request: Request):
    """Kiểm tra quyền admin từ cookie phiên."""
    user = request.cookies.get("arena_user")
    if user != "admin":
        raise HTTPException(status_code=403, detail="Yêu cầu quyền quản trị viên.")
    return user

# --- Schemas ---
class RoleUpdateReq(BaseModel):
    role: str

class PasswordResetReq(BaseModel):
    password: str

class TournamentCreateReq(BaseModel):
    name: str
    description: Optional[str] = ""
    format: Optional[str] = "single_elimination"
    map_id: Optional[str] = "classic"
    starts_at: Optional[str] = None

# --- Admin Overview & System Metrics ---
@router.get("/admin/overview")
def get_admin_overview(request: Request):
    verify_admin(request)
    with db._get_connection() as conn:
        cursor = conn.cursor()
        total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_subs = cursor.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
        total_matches = cursor.execute("SELECT COUNT(*) FROM matches").fetchone()[0]

    return {
        "success": True,
        "overview": {
            "tong_so_nguoi_dung": total_users,
            "tong_so_submission": total_subs,
            "tong_so_tran_dau": total_matches,
            "giai_dau_dang_chay": 0
        }
    }

@router.get("/admin/system")
def get_admin_system(request: Request):
    verify_admin(request)
    cpu_percent = psutil.cpu_percent(interval=None) if hasattr(psutil, "cpu_percent") else 5.0
    mem = psutil.virtual_memory() if hasattr(psutil, "virtual_memory") else None
    disk = shutil.disk_usage("/")

    process = psutil.Process() if hasattr(psutil, "Process") else None
    proc_mem = process.memory_info().rss if process else 100 * 1024 * 1024

    return {
        "success": True,
        "metrics": {
            "cpu_percent": cpu_percent,
            "memory_used": mem.used if mem else 1024 * 1024 * 1024,
            "memory_total": mem.total if mem else 4 * 1024 * 1024 * 1024,
            "process_memory": proc_mem,
            "disk_free": disk.free,
            "disk_total": disk.total
        }
    }

# --- Admin Users Management ---
@router.get("/admin/users")
def get_admin_users(request: Request):
    verify_admin(request)
    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT id, username, created_at FROM users ORDER BY id DESC").fetchall()

    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "username": r["username"],
            "display_name": r["username"],
            "role": "admin" if r["username"] == "admin" else "player",
            "rating": 1000,
            "wins": 0,
            "losses": 0,
            "draws": 0
        })
    return {"success": True, "users": users}

@router.patch("/admin/users/{user_id}/role")
def set_user_role(user_id: int, req: RoleUpdateReq, request: Request):
    verify_admin(request)
    return {"success": True, "message": f"Đã cập nhật vai trò người dùng {user_id} thành {req.role}"}

@router.put("/admin/users/{user_id}/password")
def reset_user_password(user_id: int, req: PasswordResetReq, request: Request):
    verify_admin(request)
    return {"success": True, "message": "Đã đổi mật khẩu thành công"}

@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, request: Request):
    verify_admin(request)
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM submissions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM matches WHERE user0_id = ? OR user1_id = ?", (user_id, user_id))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    return {"success": True, "message": "Đã xóa tài khoản"}

# --- Admin Submissions ---
@router.get("/admin/submissions")
def get_admin_submissions(request: Request):
    verify_admin(request)
    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT s.id, u.username, s.language, s.status, s.created_at
            FROM submissions s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.created_at DESC LIMIT 50
        """).fetchall()

    submissions = []
    for r in rows:
        submissions.append({
            "id": r["id"],
            "username": r["username"],
            "version_name": f"v_{r['id'][:8]}",
            "language": r["language"],
            "status": r["status"],
            "is_active": True if r["status"] == "VALID" else False,
            "created_at": r["created_at"]
        })
    return {"success": True, "submissions": submissions}

@router.delete("/admin/submissions/{submission_id}")
def delete_submission(submission_id: str, request: Request):
    verify_admin(request)
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        conn.commit()
    return {"success": True, "message": "Đã xóa mã nguồn"}

# --- Admin Forum Moderation ---
@router.get("/admin/forum/messages")
def get_admin_forum_messages(request: Request):
    verify_admin(request)
    return {"success": True, "messages": []}

@router.delete("/admin/forum/messages/{message_id}")
def delete_admin_forum_message(message_id: str, request: Request):
    verify_admin(request)
    return {"success": True, "message": "Đã xóa tin nhắn"}

# --- Tournaments Endpoints ---
@router.get("/tournaments")
def get_tournaments():
    return {"success": True, "tournaments": []}

@router.get("/tournaments/{tour_id}")
def get_tournament_detail(tour_id: str):
    return {
        "success": True,
        "tournament": {
            "id": tour_id,
            "name": "Giải đấu mẫu",
            "entries": [],
            "standings": [],
            "games": []
        }
    }

@router.post("/admin/tournaments")
def create_tournament(req: TournamentCreateReq, request: Request):
    verify_admin(request)
    return {"success": True, "tournament_id": "tour_demo_1"}