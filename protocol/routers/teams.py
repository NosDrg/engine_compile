# protocol/routers/teams.py
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/teams", tags=["Teams"])

class TeamCreateReq(BaseModel):
    name: str

class TeamJoinReq(BaseModel):
    join_code: str

@router.get("/me")
def get_my_team(request: Request):
    # Trả về team rỗng nếu người dùng chưa tạo/tham gia đội
    return {"success": True, "team": None}

@router.post("")
def create_team(req: TeamCreateReq, request: Request):
    return {
        "success": True,
        "join_code": "TEAM1234",
        "team": {
            "id": 1,
            "name": req.name,
            "member_role": "owner",
            "members": []
        }
    }

@router.post("/join")
def join_team(req: TeamJoinReq, request: Request):
    return {"success": True, "message": "Đã tham gia đội"}

@router.post("/leave")
def leave_team(request: Request):
    return {"success": True, "message": "Đã rời đội"}