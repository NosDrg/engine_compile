# protocol/routers/auth.py
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Optional
from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api", tags=["Auth"])
db = DatabaseManager(DEFAULT_DB_PATH)

ADMIN_USERNAMES = {"admin"}

class LoginReq(BaseModel):
    username: str
    password: str
    remember: bool = False

class RegisterReq(BaseModel):
    username: str
    display_name: Optional[str] = None
    password: str
    preferred_language: Optional[str] = "python"


@router.post("/register")
def register(req: RegisterReq, response: Response):
    user_id = db.get_or_create_user(req.username)
    response.set_cookie(key="arena_user", value=req.username, httponly=False, samesite="lax")
    return {
        "success": True,
        "user": {
            "id": user_id,
            "username": req.username,
            "display_name": req.display_name or req.username,
            "role": "player"
        }
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="arena_user")
    return {"success": True}


def build_user_payload(user_id: int, username: str):
    is_admin = username in ADMIN_USERNAMES
    payload = {
        "id": user_id,
        "username": username,
        "display_name": username,
    }
    if is_admin:
        payload["extra_nav"] = [
            {"title": "Quản trị", "path": "/admin/"}
        ]
    return payload

@router.get("/me")
def get_current_user(request: Request):
    username = request.cookies.get("arena_user")
    if not username:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")

    user_id = db.get_or_create_user(username)
    return {"user": build_user_payload(user_id, username)}

@router.post("/login")
def login(req: BaseModel, response: Response):
    user_id = db.get_or_create_user(req.username)
    response.set_cookie(key="arena_user", value=req.username, httponly=False, samesite="lax")
    return {
        "success": True,
        "user": build_user_payload(user_id, req.username)
    }


class ProfileUpdateReq(BaseModel):
    display_name: Optional[str] = None
    avatar_id: Optional[str] = "robot"
    bio: Optional[str] = ""
    profile_public: Optional[bool] = True

class PasswordChangeReq(BaseModel):
    current_password: str
    new_password: str

@router.patch("/account/profile")
def update_profile(req: ProfileUpdateReq, request: Request):
    username = request.cookies.get("arena_user") or "anonymous"
    user_id = db.get_or_create_user(username)
    user_data = build_user_payload(user_id, username)
    user_data.update({
        "display_name": req.display_name or username,
        "avatar_id": req.avatar_id,
        "bio": req.bio,
        "profile_public": req.profile_public
    })
    return {"success": True, "user": user_data}

@router.post("/account/password")
def change_password(req: PasswordChangeReq, request: Request):
    return {"success": True, "message": "Đã đổi mật khẩu thành công."}