# protocol/routers/admin.py
import shutil
import psutil
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, status # type: ignore
from routers.auth import get_current_user

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH

# Đổi prefix về "/api" để khớp chính xác với frontend api.js
router = APIRouter(prefix="/api", tags=["Admin"])
db = DatabaseManager(DEFAULT_DB_PATH)

def require_admin(user: Dict[str, Any] = Depends(get_current_user)):
    """Kiểm tra quyền admin từ JWT Token."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Yêu cầu quyền quản trị viên."
        )
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
def get_admin_overview(admin: Dict[str, Any] = Depends(require_admin)):
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
def get_admin_system(admin: Dict[str, Any] = Depends(require_admin)):
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
def get_admin_users(admin: Dict[str, Any] = Depends(require_admin)):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT id, username, display_name, role, created_at FROM users ORDER BY id DESC").fetchall()

    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "username": r["username"],
            "display_name": r["display_name"] or r["username"],
            "role": r["role"] or "player",
            "rating": 1000,
            "wins": 0,
            "losses": 0,
            "draws": 0
        })
    return {"success": True, "users": users}

@router.patch("/admin/users/{user_id}/role")
def set_user_role(user_id: int, req: RoleUpdateReq, admin: Dict[str, Any] = Depends(require_admin)):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (req.role, user_id))
        conn.commit()
    return {"success": True, "message": f"Đã cập nhật vai trò người dùng {user_id} thành {req.role}"}

@router.put("/admin/users/{user_id}/password")
def reset_user_password(user_id: int, req: PasswordResetReq, admin: Dict[str, Any] = Depends(require_admin)):
    import hashlib
    new_hash = hashlib.sha256(req.password.encode()).hexdigest()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        conn.commit()
    return {"success": True, "message": "Đã đổi mật khẩu thành công"}

@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM submissions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM matches WHERE user0_id = ? OR user1_id = ?", (user_id, user_id))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    return {"success": True, "message": "Đã xóa tài khoản"}

# --- Admin Submissions ---
@router.get("/admin/submissions")
def get_admin_submissions(admin: Dict[str, Any] = Depends(require_admin)):
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
def delete_submission(submission_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        conn.commit()
    return {"success": True, "message": "Đã xóa mã nguồn"}

# --- Admin Forum Moderation ---
@router.get("/admin/forum/messages")
def get_admin_forum_messages(admin: Dict[str, Any] = Depends(require_admin)):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT id, username, display_name, body, created_at FROM forum_messages ORDER BY id DESC LIMIT 50").fetchall()
    return {"success": True, "messages": [dict(r) for r in rows]}

@router.delete("/admin/forum/messages/{message_id}")
def delete_admin_forum_message(message_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM forum_messages WHERE id = ?", (message_id,))
        cursor.execute("INSERT INTO forum_deletions (message_id) VALUES (?)", (message_id,))
        conn.commit()
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
def create_tournament(req: TournamentCreateReq, admin: Dict[str, Any] = Depends(require_admin)):
    return {"success": True, "tournament_id": "tour_demo_1"}


# --- Dynamic Game & Runtime Studio Endpoints ---
class GameUpsertReq(BaseModel):
    slug: str
    name: str
    description: Optional[str] = ""
    board_type: Optional[str] = "grid_9x9"
    referee_code: str
    starter_bot_code: Optional[str] = ""
    is_active: Optional[int] = 1

class RefereeTestReq(BaseModel):
    referee_code: str

class RuntimeUpsertReq(BaseModel):
    id: str
    name: str
    extension: str
    compile_cmd: Optional[str] = ""
    run_cmd: str
    timeout_sec: Optional[float] = 2.0
    memory_limit_mb: Optional[int] = 128
    is_enabled: Optional[int] = 1

@router.get("/admin/games")
def get_admin_games(admin: Dict[str, Any] = Depends(require_admin)):
    """Lấy danh sách tất cả các trò chơi đã cấu hình trong hệ thống."""
    return {"success": True, "games": db.get_all_games()}

@router.post("/admin/games")
def upsert_admin_game(req: GameUpsertReq, admin: Dict[str, Any] = Depends(require_admin)):
    """
    Tạo hoặc cập nhật cấu hình trò chơi:
    - Kiểm tra cú pháp Python của referee_code bằng compile(..., 'exec').
    - Kiểm tra sự tồn tại của 3 hàm bắt buộc: init_game, validate_move, apply_move.
    - Lưu vào SQLite qua db.upsert_game.
    """
    # 1. Kiểm tra cú pháp Python
    try:
        code_obj = compile(req.referee_code, '<referee_validator>', 'exec')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi cú pháp Python trong mã trọng tài: {str(e)}"
        )

    # 2. Kiểm tra sự tồn tại của 3 hàm giao thức
    scope: Dict[str, Any] = {}
    try:
        exec(code_obj, scope)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi khi thực thi khởi tạo mã trọng tài: {str(e)}"
        )

    required_funcs = ["init_game", "validate_move", "apply_move"]
    for fn in required_funcs:
        if fn not in scope or not callable(scope[fn]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã trọng tài thiếu hàm bắt buộc '{fn}' theo giao thức trọng tài."
            )

    # 3. Lưu vào Database
    db.upsert_game(req.dict())
    return {"success": True, "message": f"Đã lưu trò chơi '{req.name}' ({req.slug}) thành công!"}

@router.post("/admin/games/test-referee")
def test_admin_referee(req: RefereeTestReq, admin: Dict[str, Any] = Depends(require_admin)):
    """
    Chạy Dry-Run thử nghiệm mã nguồn trọng tài Python:
    - Gọi init_game() lấy state ban đầu.
    - Thử validate_move với nước đi giả lập {"row": 0, "col": 0}.
    - Nếu hợp lệ, thử apply_move và trả về kết quả xem trước.
    """
    try:
        code_obj = compile(req.referee_code, '<test_dry_run>', 'exec')
        scope: Dict[str, Any] = {}
        exec(code_obj, scope)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi biên dịch Python: {str(e)}"
        )

    for fn in ["init_game", "validate_move", "apply_move"]:
        if fn not in scope or not callable(scope[fn]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Thiếu hàm bắt buộc '{fn}' trong mã trọng tài."
            )

    try:
        init_state = scope["init_game"]()
        mock_move = {"row": 0, "col": 0}
        is_valid = scope["validate_move"](init_state, mock_move, 0)
        apply_res = None
        if is_valid:
            new_state, winner, reason = scope["apply_move"](init_state, mock_move, 0)
            apply_res = {
                "new_state": new_state,
                "winner": winner,
                "reason": reason
            }

        return {
            "success": True,
            "message": "Kiểm thử mã trọng tài thành công (Dry-Run hoàn tất).",
            "init_state": init_state,
            "mock_move": mock_move,
            "is_valid": is_valid,
            "apply_result": apply_res
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi khi thực thi dry-run: {str(e)}"
        )

@router.get("/admin/runtimes")
def get_admin_runtimes(admin: Dict[str, Any] = Depends(require_admin)):
    """Lấy danh sách các môi trường runtime biên dịch bot."""
    return {"success": True, "runtimes": db.get_runtimes(enabled_only=False)}

@router.post("/admin/runtimes")
def upsert_admin_runtime(req: RuntimeUpsertReq, admin: Dict[str, Any] = Depends(require_admin)):
    """Tạo hoặc cập nhật cấu hình runtime trình biên dịch bot."""
    db.upsert_runtime(req.dict())
    return {"success": True, "message": f"Đã lưu cấu hình runtime '{req.id}' thành công."}
