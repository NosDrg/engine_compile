# protocol/app.py
import os
import sys
import jwt
from contextlib import asynccontextmanager

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import FRONTEND_DIR
from routers.auth import JWT_SECRET, JWT_ALGORITHM
from routers import submissions, matches, auth, stats, notifications, admin, forum, teams, missions

# 1. Khởi tạo vòng đời ứng dụng (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động service nếu có, yield để app chạy
    yield

# 2. KHỞI TẠO DUY NHẤT 1 ĐỐI TƯỢNG APP
app = FastAPI(
    title="Match Arena API",
    version="1.0.0",
    lifespan=lifespan
)

# 3. Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. ĐĂNG KÝ TOÀN BỘ CÁC ROUTER API (Bắt buộc phải nằm sau khi khởi tạo app)
app.include_router(auth.router)
app.include_router(submissions.router)
app.include_router(matches.router)
app.include_router(stats.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(forum.router)
app.include_router(teams.router)
app.include_router(missions.router)

# 5. Phục vụ bảng điều khiển Admin
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
        return RedirectResponse(url="/login.html?redirect=/admin/index.html")
    
    target_path = os.path.join(FRONTEND_DIR, "admin", file_path or "index.html")
    if os.path.exists(target_path) and os.path.isfile(target_path):
        return FileResponse(target_path)
    raise HTTPException(status_code=404, detail="File not found")

# 6. Mount Static Files Frontend (BẮT BUỘC nằm ở cuối cùng)
if os.path.isdir(FRONTEND_DIR):
    print(f"[INFO] Frontend mounted thành công từ: {FRONTEND_DIR}")
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"[WARN] Không tìm thấy thư mục frontend tại: {FRONTEND_DIR}")