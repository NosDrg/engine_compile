# protocol/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class SubmitReq(BaseModel):
    username: str = Field(..., min_length=1, description="Tên thí sinh")
    language: str = Field(..., description="python, cpp, java")
    source_code: str = Field(..., min_length=1, description="Mã nguồn của bot")

class ValidateReq(BaseModel):
    language: str
    source_code: str

class MatchReq(BaseModel):
    user0: str = Field(..., description="Username hoặc sub_id của Player 0")
    user1: str = Field(..., description="Username hoặc sub_id của Player 1")
    ranked: Optional[bool] = False
    seed: Optional[int] = None
    map_id: Optional[str] = "classic"