# protocol/routers/teams.py
from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from routers.auth import get_current_user

router = APIRouter(prefix="/api/teams", tags=["Teams"])

class TeamCreateReq(BaseModel):
    name: str

class TeamJoinReq(BaseModel):
    join_code: str

@router.get("/me")
def get_my_team(user: Dict[str, Any] = Depends(get_current_user)):
    return {"success": True, "team": None}

@router.post("")
def create_team(req: TeamCreateReq, user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "success": True,
        "join_code": "TEAM1234",
        "team": {
            "id": 1,
            "name": req.name,
            "member_role": "owner",
            "members": [{"user_id": user["id"], "username": user["username"], "role": "owner"}]
        }
    }

@router.post("/join")
def join_team(req: TeamJoinReq, user: Dict[str, Any] = Depends(get_current_user)):
    return {"success": True, "message": "Đã tham gia đội"}

@router.post("/leave")
def leave_team(user: Dict[str, Any] = Depends(get_current_user)):
    return {"success": True, "message": "Đã rời đội"}