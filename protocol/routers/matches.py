# protocol/routers/matches.py
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH
from core.allocator import core_allocator
from services.match_service import match_service

router = APIRouter(prefix="/api", tags=["Matches"])
db = DatabaseManager(DEFAULT_DB_PATH)

class MatchReq(BaseModel):
    user0: str
    user1: str

@router.post("/duel")
def run_duel(req: MatchReq):
    c0, c1 = core_allocator.get_pair()
    try:
        res = match_service.run_match(req.user0, req.user1, core0=c0, core1=c1)
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error"))
        return res
    finally:
        core_allocator.release_pair(c0, c1)

@router.get("/opponents")
def get_opponents(exclude: Optional[str] = None):
    opponents = db.get_all_valid_opponents(exclude_username=exclude)
    return {"success": True, "opponents": opponents}

@router.get("/matches")
def get_recent_matches():
    with db._get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT m.id, m.reason, m.created_at,
                   u0.username as user0_name,
                   u1.username as user1_name,
                   uw.username as winner_name
            FROM matches m
            JOIN users u0 ON m.user0_id = u0.id
            JOIN users u1 ON m.user1_id = u1.id
            LEFT JOIN users uw ON m.winner_user_id = uw.id
            ORDER BY m.created_at DESC
            LIMIT 20
        """).fetchall()

    return {"success": True, "matches": [dict(r) for r in rows]}

@router.get("/matches/{match_id}")
def get_match_replay(match_id: str):
    match_data = db.get_match_by_id(match_id)
    if not match_data:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy ván đấu {match_id}")
    return {
        "success": True,
        "match_id": match_data["id"],
        "summary": {
            "winner_name": match_data["winner_name"] or "Hòa",
            "reason": match_data["reason"],
            "created_at": match_data["created_at"]
        },
        "metrics": {
            "player_0": {
                "username": match_data["user0_name"],
                "language": match_data["user0_lang"],
                "peak_ram_mb": match_data["bot0_ram_mb"]
            },
            "player_1": {
                "username": match_data["user1_name"],
                "language": match_data["user1_lang"],
                "peak_ram_mb": match_data["bot1_ram_mb"]
            }
        },
        "replay": match_data["replay_data"]
    }