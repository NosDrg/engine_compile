# protocol/routers/auth.py
import hashlib
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel, ConfigDict

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH

router = APIRouter(prefix="/api", tags=["Auth"])
db = DatabaseManager(DEFAULT_DB_PATH)

class RegisterReq(BaseModel):
    model_config = ConfigDict(extra="allow")
    username: Optional[str] = None
    account: Optional[str] = None
    password: str
    display_name: Optional[str] = None

class LoginReq(BaseModel):
    model_config = ConfigDict(extra="allow")
    username: Optional[str] = None
    account: Optional[str] = None
    user: Optional[str] = None
    password: str

    def get_account_name(self) -> str:
        return (self.username or self.account or self.user or "").strip()

class ProfileUpdateReq(BaseModel):
    display_name: Optional[str] = None
    avatar_id: Optional[str] = "robot"
    bio: Optional[str] = ""
    profile_public: Optional[bool] = True

class PasswordChangeReq(BaseModel):
    current_password: str
    new_password: str

def _build_user_dict(user_row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user_row["id"],
        "username": user_row["username"],
        "display_name": user_row.get("display_name") or user_row["username"],
        "role": user_row.get("role", "player"),
        "avatar_id": user_row.get("avatar_id", "robot"),
        "bio": user_row.get("bio", ""),
        "rating": user_row.get("rating", 1000)
    }

@router.post("/register")
def register(req: RegisterReq, response: Response):
    username = (req.username or req.account or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Tên tài khoản không được để trống.")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Tên tài khoản phải có ít nhất 3 ký tự.")

    # Kiểm tra xem user đã tồn tại chưa
    existing = db.get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=400, detail="Tài khoản đã tồn tại.")

    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    display_name = req.display_name or username

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password_hash, display_name, role)
            VALUES (?, ?, ?, 'player')
        """, (username, pwd_hash, display_name))
        conn.commit()
        user_id = cursor.lastrowid

    # Đăng nhập tự động sau khi đăng ký
    response.set_cookie(key="arena_user", value=username, httponly=False, max_age=86400 * 7, samesite="lax")

    return {
        "success": True,
        "message": "Đăng ký thành công",
        "user": {
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "role": "player",
            "rating": 1000
        }
    }

@router.post("/login")
def login(req: LoginReq, response: Response):
    username = req.get_account_name()
    if not username:
        raise HTTPException(status_code=400, detail="Vui lòng nhập tên tài khoản.")

    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không chính xác.")

    # Xác thực mật khẩu
    if user.get("password_hash"):
        input_hash = hashlib.sha256(req.password.encode()).hexdigest()
        if user["password_hash"] != input_hash:
            raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không chính xác.")

    response.set_cookie(key="arena_user", value=username, httponly=False, max_age=86400 * 7, samesite="lax")

    return {
        "success": True,
        "message": "Đăng nhập thành công",
        "user": _build_user_dict(user)
    }

@router.get("/me")
def get_current_user(request: Request):
    username = request.cookies.get("arena_user")
    if not username:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập.")

    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ.")

    return {
        "success": True,
        "user": _build_user_dict(user)
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="arena_user")
    return {"success": True, "message": "Đã đăng xuất."}

@router.patch("/account/profile")
def update_profile(req: ProfileUpdateReq, request: Request):
    username = request.cookies.get("arena_user")
    if not username:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập.")

    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

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

    user.update({"display_name": display_name, "avatar_id": avatar_id, "bio": bio})
    return {"success": True, "user": _build_user_dict(user)}

@router.post("/account/password")
def change_password(req: PasswordChangeReq, request: Request):
    username = request.cookies.get("arena_user")
    if not username:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập.")

    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    if user.get("password_hash"):
        current_hash = hashlib.sha256(req.current_password.encode()).hexdigest()
        if user["password_hash"] != current_hash:
            raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")

    new_hash = hashlib.sha256(req.new_password.encode()).hexdigest()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
        conn.commit()

    return {"success": True, "message": "Đổi mật khẩu thành công."}