# protocol/app.py
import os
import threading
from typing import Optional
from fastapi import FastAPI, HTTPException # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore
from fastapi.responses import FileResponse, RedirectResponse # type: ignore
from pydantic import BaseModel
from protocol_service import ProtocolService

app = FastAPI(title="Match Arena API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = ProtocolService()

class CoreManager:
    def __init__(self):
        total_cores = os.cpu_count() or 4
        self.available = list(range(total_cores))
        self.lock = threading.Lock()

    def get_pair(self):
        with self.lock:
            if len(self.available) >= 2:
                return self.available.pop(0), self.available.pop(0)
            return 0, 1

    def release_pair(self, c1: int, c2: int):
        with self.lock:
            if c1 not in self.available: self.available.append(c1)
            if c2 not in self.available: self.available.append(c2)

core_mgr = CoreManager()

class SubmitReq(BaseModel):
    username: str
    language: str
    source_code: str

class MatchReq(BaseModel):
    user0: str
    user1: str

# Mount static frontend
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if os.path.isdir(os.path.join(PROJECT_ROOT, "frontend")):
    FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
elif os.path.isdir(os.path.join(CURRENT_DIR, "frontend")):
    FRONTEND_DIR = os.path.join(CURRENT_DIR, "frontend")
else:
    FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

for folder in ["assets", "css", "js"]:
    folder_path = os.path.join(FRONTEND_DIR, folder)
    if os.path.isdir(folder_path):
        app.mount(f"/{folder}", StaticFiles(directory=folder_path), name=folder)

@app.get("/")
def get_ui():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return RedirectResponse(url="/docs")

@app.post("/api/submit")
def submit_code(req: SubmitReq):
    result = service.submit_code(req.username, req.language, req.source_code)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@app.post("/api/duel")
def run_duel(req: MatchReq):
    c0, c1 = core_mgr.get_pair()
    try:
        result = service.start_match(req.user0, req.user1, core0=c0, core1=c1)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    finally:
        core_mgr.release_pair(c0, c1)

@app.get("/api/matches/{match_id}")
def get_match(match_id: str):
    result = service.get_match_replay(match_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=str(result.get("error", "Not found")))
    return result

@app.get("/api/opponents")
def get_opponents(exclude: Optional[str] = None):
    opponents = service.get_all_opponents(exclude_username=exclude)
    return {"success": True, "opponents": opponents}