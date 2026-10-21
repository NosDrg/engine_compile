# protocol/routers/notifications.py
from fastapi import APIRouter, Depends # type: ignore
from routers.auth import get_current_user
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter(prefix="/api", tags=["Notifications"])

class MarkReadReq(BaseModel):
    notification_id: Optional[str] = None

@router.get("/notifications")
def get_notifications(user: Dict[str, Any] = Depends(get_current_user)):
    """Trả về danh sách thông báo và số lượng chưa đọc của user đăng nhập."""
    # Sau này có thể query bảng notifications theo user["id"]
    return {
        "success": True,
        "unread_count": 0,
        "notifications": []
    }

@router.patch("/notifications/read")
def mark_notifications_read(
    req: Optional[MarkReadReq] = None, 
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Đánh dấu thông báo đã đọc."""
    return {
        "success": True,
        "message": "Đã đánh dấu đã đọc"
    }