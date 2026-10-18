# protocol/routers/notifications.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api", tags=["Notifications"])

class MarkReadReq(BaseModel):
    notification_id: Optional[str] = None

@router.get("/notifications")
def get_notifications():
    """Trả về danh sách thông báo và số lượng chưa đọc."""
    return {
        "success": True,
        "unread_count": 0,
        "notifications": []
    }

@router.patch("/notifications/read")
def mark_notifications_read(req: MarkReadReq = None):
    """Đánh dấu thông báo đã đọc."""
    return {
        "success": True,
        "message": "Đã đánh dấu đã đọc"
    }