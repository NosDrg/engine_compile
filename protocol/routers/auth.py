# protocol/routers/auth.py
import os
import hashlib
import datetime
from typing import Optional, Dict, Any
import jwt
from fastapi import APIRouter, HTTPException, Response, Request, Depends, status
from pydantic import BaseModel, ConfigDict

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH

router = APIRouter(prefix="/api", tags=["Auth"])
db = DatabaseManager(DEFAULT_DB_PATH)

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_match_arena_jwt_key_2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

def create_access_token(user_id: int, username: str, role: str = "player") -> str:
    """Tạo JWT Token có thời hạn và chữ ký an toàn."""
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": username,
        "uid": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(request: Request) -> Dict[str, Any]:
    """Dependency lấy thông tin user từ JWT (hỗ trợ cả Cookie HttpOnly và Header Authorization)."""
    token = request.cookies.get("arena_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Yêu cầu đăng nhập để tiếp tục."
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token xác thực không hợp lệ.")

    user = db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại.")
    return user

# --- SCHEMAS ---
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

# --- ENDPOINTS ---
@router.post("/register")
def register(req: RegisterReq, response: Response):
    username = (req.username or req.account or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Tên tài khoản không được để trống.")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Tên tài khoản phải có ít nhất 3 ký tự.")

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

    # Cấp token JWT
    token = create_access_token(user_id=user_id, username=username, role="player")
    response.set_cookie(
        key="arena_token",
        value=token,
        httponly=True,  # Ngăn chặn script độc hại từ trình duyệt đọc trộm token
        max_age=86400 * ACCESS_TOKEN_EXPIRE_DAYS,
        samesite="lax"
    )

    return {
        "success": True,
        "message": "Đăng ký thành công",
        "access_token": token,
        "token_type": "bearer",
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
    password = (req.password or "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Vui lòng nhập đầy đủ tài khoản và mật khẩu.")

    user = db.get_user_by_username(username)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không chính xác.")

    input_hash = hashlib.sha256(password.encode()).hexdigest()
    if user["password_hash"] != input_hash:
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không chính xác.")

    # Cấp token JWT
    role = user.get("role", "player")
    token = create_access_token(user_id=user["id"], username=user["username"], role=role)
    response.set_cookie(
        key="arena_token",
        value=token,
        httponly=True,
        max_age=86400 * ACCESS_TOKEN_EXPIRE_DAYS,
        samesite="lax"
    )

    return {
        "success": True,
        "message": "Đăng nhập thành công",
        "access_token": token,
        "token_type": "bearer",
        "user": _build_user_dict(user)
    }

@router.get("/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "success": True,
        "user": _build_user_dict(user)
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="arena_token")
    return {"success": True, "message": "Đã đăng xuất thành công."}

@router.patch("/account/profile")
def update_profile(req: ProfileUpdateReq, user: Dict[str, Any] = Depends(get_current_user)):
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