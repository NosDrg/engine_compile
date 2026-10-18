# protocol/routers/submissions.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH
from services.match_service import match_service

router = APIRouter(prefix="/api", tags=["Submissions"])
db = DatabaseManager(DEFAULT_DB_PATH)

class SubmitReq(BaseModel):
    source_code: str
    language: str
    version_name: Optional[str] = "Submission"

class ValidateReq(BaseModel):
    source_code: str
    language: str

@router.post("/validate")
def validate_code(req: ValidateReq):
    res = match_service.validate_code_only(req.source_code, req.language)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.post("/submissions")
def submit_code(req: SubmitReq, request: Request):
    username = request.cookies.get("arena_user") or "anonymous"
    res = match_service.submit_bot(username, req.language, req.source_code)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@router.get("/submissions")
def get_user_submissions(request: Request):
    username = request.cookies.get("arena_user")
    if not username:
        return {"success": True, "submissions": []}

    user_id = db.get_or_create_user(username)
    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, language, status, error_log, created_at
            FROM submissions
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,)).fetchall()

    submissions = []
    latest_valid_id = None
    for r in rows:
        if r["status"] == "VALID" and latest_valid_id is None:
            latest_valid_id = r["id"]

    for r in rows:
        submissions.append({
            "id": r["id"],
            "version_name": f"v_{r['id'][:8]}",
            "language": r["language"],
            "status": r["status"],
            "is_active": (r["id"] == latest_valid_id),
            "error_log": r["error_log"] or "",
            "created_at": r["created_at"]
        })

    return {"success": True, "submissions": submissions}

@router.post("/submissions/{sub_id}/activate")
def activate_submission(sub_id: str, request: Request):
    return {"success": True, "message": f"Đã kích hoạt phiên bản {sub_id}"}