# protocol/app.py
import os
import sys
import jwt
from fastapi import FastAPI, Request, HTTPException # type: ignore
from fastapi.responses import FileResponse, RedirectResponse # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore

from config import FRONTEND_DIR
from routers.auth import JWT_SECRET, JWT_ALGORITHM
from routers import submissions, matches, auth, stats, notifications, admin, forum, teams, missions, contests, users


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


app = FastAPI(title="Match Arena API", version="1.0.0")

# SỬA LỖI CORS: Không dùng allow_origins=["*"] khi allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_origin_regex=r"https?://.*", # Hỗ trợ mọi domain khi deploy lên Render/Cloud
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router API
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(contests.router)
app.include_router(submissions.router)
app.include_router(matches.router)
app.include_router(stats.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(forum.router)  
app.include_router(teams.router)
app.include_router(missions.router)

# SỬA LỖI TRUY CẬP TRANG ADMIN: Giải mã JWT token thay vì đọc cookie cũ
@app.get("/admin/{file_path:path}")
def serve_admin_panel(request: Request, file_path: str = ""):
    token = request.cookies.get("arena_token")
    is_admin = False
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("role") == "admin" or payload.get("sub") == "admin":
                is_admin = True
        except Exception:
            pass

    if not is_admin:
        # Nếu chưa đăng nhập admin, chuyển hướng về trang đăng nhập
        return RedirectResponse(url="/login.html?redirect=/admin/index.html")
    
    target_path = os.path.join(FRONTEND_DIR, "admin", file_path or "index.html")
    if os.path.exists(target_path) and os.path.isfile(target_path):
        return FileResponse(target_path)
    raise HTTPException(status_code=404, detail="File not found")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
