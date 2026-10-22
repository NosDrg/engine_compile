# protocol/routers/contests.py
import os
import sys
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, HTTPException, Request, Depends, status # type: ignore

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_DIR = os.path.dirname(CURRENT_DIR)
if PROTOCOL_DIR not in sys.path:
    sys.path.insert(0, PROTOCOL_DIR)

from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH
from routers.auth import get_current_user
from routers.admin import require_admin
from services.contest_evaluator import contest_evaluator

router = APIRouter(tags=["Contests"])
db = DatabaseManager(DEFAULT_DB_PATH)

def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    try:
        return get_current_user(request)
    except Exception:
        return None

# --- Schemas ---
class TestSuiteReq(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_code: str
    language: Optional[str] = "python"
    blur_count: Optional[int] = 0
    total_blur_sec: Optional[int] = 0

class ContestSubmitReq(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_code: Optional[str] = None
    language: Optional[str] = "python"

class TestCaseCreateReq(BaseModel):
    name: str
    initial_board_state: str
    expected_constraint: Optional[str] = '{"type": "empty_cell"}'
    timeout_ms: Optional[int] = 1000

class ContestCreateReq(BaseModel):
    id: Optional[str] = None
    title: str
    game_slug: str = "default"
    start_time: str
    duration_minutes: int = 60
    max_memory_mb: Optional[int] = 128
    run_timeout_sec: Optional[float] = 2.0
    rounds_per_pair: Optional[int] = 3
    status: Optional[str] = "RUNNING"
    test_cases: Optional[List[TestCaseCreateReq]] = None


# --- Contests API Endpoints ---

@router.get("/api/contests/active")
def get_active_contest(request: Request):
    """
    Trả về thông tin contest đang mở (hoặc sắp mở), thời gian còn lại (remaining_seconds),
    slug của game, danh sách test case (chỉ hiển thị tên & giới hạn, không lộ state),
    và bản draft hiện tại của người dùng nếu đã đăng nhập.
    """
    contest = db.get_active_contest()
    if not contest:
        raise HTTPException(status_code=404, detail="Hiện không có cuộc thi nào đang diễn ra.")

    test_cases = db.get_contest_test_cases(contest["id"], public_only=True)
    user = get_optional_user(request)
    my_draft = None
    if user:
        my_draft = db.get_user_contest_draft(contest["id"], user["id"])

    return {
        "success": True,
        "contest": contest,
        "test_cases": test_cases,
        "my_draft": my_draft
    }


@router.post("/api/contests/{contest_id}/test-suite")
def run_contest_test_suite(
    contest_id: str,
    req: TestSuiteReq,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Chạy bộ test case nhân tạo trong sandbox và tự động cập nhật draft cho thí sinh.
    """
    contest = db.get_contest(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy cuộc thi {contest_id}")

    res = contest_evaluator.run_bot_synthetic_tests(
        contest_id=contest_id,
        source_code=req.source_code,
        language=req.language or "python"
    )

    # Tự động lưu kết quả vào contest_drafts
    draft_id = db.save_contest_draft(
        contest_id=contest_id,
        user_id=user["id"],
        lang=req.language or "python",
        code=req.source_code,
        passed=res.get("passed", 0),
        total=res.get("total", 0),
        avg_speed=res.get("avg_time_ms", 0.0),
        blur_count=req.blur_count or 0,
        blur_sec=req.total_blur_sec or 0
    )

    return {
        "success": res.get("success", False),
        "passed": res.get("passed", 0),
        "total": res.get("total", 0),
        "avg_time_ms": res.get("avg_time_ms", 0.0),
        "details": res.get("details", []),
        "draft_id": draft_id
    }


@router.post("/api/contests/{contest_id}/submit")
def submit_contest_bot(
    contest_id: str,
    req: Optional[ContestSubmitReq] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Cho phép thí sinh chủ động chốt bản nộp chính thức trước khi hết giờ.
    """
    contest = db.get_contest(contest_id)
    if not contest:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy cuộc thi {contest_id}")

    sub_res = db.set_user_contest_submission(
        contest_id=contest_id,
        user_id=user["id"],
        source_code=req.source_code if req else None,
        language=req.language if req else None
    )

    return {
        "success": True,
        "message": "Nộp bài chính thức thành công! Thuật toán của bạn đã được ghi nhận vào danh sách thi đấu.",
        "submission_id": sub_res.get("submission_id")
    }


@router.get("/api/contests/{contest_id}/leaderboard")
def get_contest_leaderboard(contest_id: str):
    """
    Trả về bảng xếp hạng giải đấu (kèm số trận Thắng/Hòa/Thua, tổng điểm, thứ hạng).
    """
    leaderboard = db.get_contest_leaderboard(contest_id)
    return {
        "success": True,
        "contest_id": contest_id,
        "leaderboard": leaderboard
    }


@router.post("/api/contests/{contest_id}/evaluate")
def trigger_contest_evaluation(contest_id: str):
    """
    Kích hoạt tiến trình xếp hạng và thi đấu Round-Robin cho cuộc thi.
    Được gọi tự động khi hết giờ hoặc bởi hệ thống/admin.
    """
    res = contest_evaluator.run_contest_round_robin(contest_id)
    return res


# --- Admin API for Contests ---

@router.post("/api/admin/contests")
def create_contest(
    req: ContestCreateReq,
    admin: Dict[str, Any] = Depends(require_admin)
):
    """
    API dành cho Admin tạo contest: chọn game, đặt thời gian, thêm test case,
    cấu hình RAM/CPU và kích hoạt giải đấu.
    """
    data = req.model_dump()
    if data.get("test_cases"):
        data["test_cases"] = [dict(tc) for tc in data["test_cases"]]
    
    cid = db.create_contest(data)
    return {
        "success": True,
        "message": f"Tạo kỳ thi '{req.title}' thành công.",
        "contest_id": cid
    }
