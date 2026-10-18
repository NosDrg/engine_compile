# protocol/app.py
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import FRONTEND_DIR
from routers import submissions, matches, auth, stats, notifications, admin, forum, teams, missions
app = FastAPI(title="Match Arena API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router API
app.include_router(auth.router)
app.include_router(submissions.router)
app.include_router(matches.router)
app.include_router(stats.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(forum.router)  
app.include_router(teams.router)
app.include_router(missions.router)

@app.get("/admin/{file_path:path}")
def serve_admin_panel(request: Request, file_path: str = ""):
    username = request.cookies.get("arena_user")
    if username != "admin":
        raise HTTPException(status_code=404, detail="Not Found")
    
    target_path = os.path.join(FRONTEND_DIR, "admin", file_path or "index.html")
    if os.path.exists(target_path) and os.path.isfile(target_path):
        return FileResponse(target_path)
    return HTTPException(status_code=404, detail="File not found")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")