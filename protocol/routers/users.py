# protocol/routers/users.py
import os
import sys
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, HTTPException, Depends, status # type: ignore

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_DIR = os.path.dirname(CURRENT_DIR)
if PROTOCOL_DIR not in sys.path:
    sys.path.insert(0, PROTOCOL_DIR)

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH
from routers.auth import get_current_user

router = APIRouter(prefix="/api/user", tags=["User Profile"])
db = DatabaseManager(DEFAULT_DB_PATH)

class ChangePasswordReq(BaseModel):
    model_config = ConfigDict(extra="allow")
    current_password: str
    new_password: str

class UpdateProfileReq(BaseModel):
    model_config = ConfigDict(extra="allow")
    display_name: Optional[str] = None
    avatar_id: Optional[str] = None
    bio: Optional[str] = None

@router.get("/profile")
def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Trả về thông tin chi tiết tài khoản, rating ELO, huy hiệu thứ hạng,
    tỷ lệ thắng trận và thống kê giải đấu ICPC.
    """
    profile = db.get_user_profile(user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin tài khoản.")
    return {
        "success": True,
        "user": profile
    }

@router.patch("/profile")
def update_current_user_profile(req: UpdateProfileReq, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Cập nhật tên hiển thị, ảnh đại diện hoặc tiểu sử người dùng.
    """
    display_name = req.display_name or user["display_name"]
    avatar_id = req.avatar_id or user.get("avatar_id", "robot")
    bio = req.bio if req.bio is not None else user.get("bio", "")

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET display_name = ?, avatar_id = ?, bio = ?
            WHERE id = ?
        """, (display_name, avatar_id, bio, user["id"]))
        conn.commit()

    profile = db.get_user_profile(user["id"])
    return {
        "success": True,
        "message": "Cập nhật hồ sơ thành công.",
        "user": profile
    }

@router.get("/history")
def get_current_user_history(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Trả về danh sách trận đấu và lịch sử tham gia các kỳ contest của user hiện tại.
    """
    history = db.get_user_history(user["id"])
    return {
        "success": True,
        "matches": history.get("matches", []),
        "contests": history.get("contests", [])
    }

@router.post("/change-password")
def change_password(req: ChangePasswordReq, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Đổi mật khẩu: xác thực mật khẩu cũ (SHA256) và cập nhật mật khẩu mới.
    """
    if len(req.new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có ít nhất 6 ký tự.")

    ok, msg = db.change_user_password(user["id"], req.current_password, req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    return {
        "success": True,
        "message": msg
    }
