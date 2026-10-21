# protocol/routers/submissions.py
import re
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH
from services.match_service import match_service
from routers.auth import get_current_user

router = APIRouter(prefix="/api", tags=["Submissions"])
db = DatabaseManager(DEFAULT_DB_PATH)

# Danh sách regex kiểm tra an toàn mã nguồn có sẵn trong mã gốc
DANGEROUS_PATTERNS = [
    r"import\s+os", r"import\s+sys", r"import\s+subprocess",
    r"import\s+socket", r"import\s+requests", r"import\s+urllib",
    r"open\(", r"eval\(", r"exec\(", r"__import__", r"system\("
]


class SubmitReq(BaseModel):
    source_code: str
    language: str
    version_name: Optional[str] = "Submission"


class ValidateReq(BaseModel):
    source_code: str
    language: str


def check_code_safety(source_code: str):
    """Quét mã nguồn theo mảng DANGEROUS_PATTERNS trước khi cho phép chạy."""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, source_code, re.IGNORECASE):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã nguồn bị từ chối do chứa lệnh/thư viện không an toàn: '{pattern}'"
            )


@router.post("/validate")
def validate_code(req: ValidateReq):
    # Kiểm tra an toàn trước khi biên dịch/thực thi thử
    check_code_safety(req.source_code)
    
    res = match_service.validate_code_only(req.source_code, req.language)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.post("/submissions")
def submit_code(req: SubmitReq, user: Dict[str, Any] = Depends(get_current_user)):
    # 1. Quét an toàn mã nguồn
    check_code_safety(req.source_code)

    # 2. Lấy username đã được xác thực an toàn từ JWT Token
    username = user["username"]

    # 3. Chạy qua match_service gốc
    res = match_service.submit_bot(username, req.language, req.source_code)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.get("/submissions")
def get_user_submissions(user: Dict[str, Any] = Depends(get_current_user)):
    # Lấy trực tiếp user_id từ tài khoản đã đăng nhập qua JWT
    user_id = user["id"]

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
def activate_submission(sub_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    # Đảm bảo chỉ người sở hữu bot mới được kích hoạt phiên bản
    with db._get_connection() as conn:
        cursor = conn.cursor()
        sub = cursor.execute("SELECT id, user_id FROM submissions WHERE id = ?", (sub_id,)).fetchone()
        if not sub:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản submission này.")
        if sub["user_id"] != user["id"] and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Bạn không có quyền kích hoạt bot