# protocol/services/match_service.py
import uuid
from typing import Dict, Any, Optional
from config import DEFAULT_ENGINE_BIN, DEFAULT_WORKSPACE_DIR, DEFAULT_DRIVERS_DIR, DEFAULT_DB_PATH
from database.db_manager import DatabaseManager
from engine.adapter import RustEngineAdapter

class MatchService:
    def __init__(self,
                 engine_bin: str = DEFAULT_ENGINE_BIN,
                 workspace_dir: str = DEFAULT_WORKSPACE_DIR,
                 drivers_dir: str = DEFAULT_DRIVERS_DIR,
                 db_path: str = DEFAULT_DB_PATH):
        self.db = DatabaseManager(db_path)
        self.engine = RustEngineAdapter(engine_bin, workspace_dir, drivers_dir)

    def submit_bot(self, username: str, language: str, source_code: str) -> Dict[str, Any]:
        user_id = self.db.get_or_create_user(username)
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"

        val_result = self.engine.validate_code(sub_id, source_code, language)
        if val_result.get("success"):
            self.db.save_submission(sub_id, user_id, language, source_code, status="VALID")
            return {
                "success": True,
                "submission_id": sub_id,
                "message": "Nộp code và kiểm tra cú pháp thành công!"
            }
        else:
            err_msg = val_result.get("error", "Lỗi cú pháp không xác định")
            self.db.save_submission(sub_id, user_id, language, source_code, status="COMPILE_ERROR", error_log=err_msg)
            return {"success": False, "submission_id": sub_id, "error": err_msg}

    def validate_code_only(self, source_code: str, language: str) -> Dict[str, Any]:
        temp_id = f"val_{uuid.uuid4().hex[:6]}"
        return self.engine.validate_code(temp_id, source_code, language)

    def run_match(self, username0: str, username1: str, core0: int, core1: int) -> Dict[str, Any]:
        user0_id = self.db.get_or_create_user(username0)
        user1_id = self.db.get_or_create_user(username1)

        sub0 = self.db.get_latest_valid_submission(user0_id)
        sub1 = self.db.get_latest_valid_submission(user1_id)

        if not sub0:
            return {"success": False, "error": f"Người chơi {username0} chưa có bài nộp hợp lệ nào."}
        if not sub1:
            return {"success": False, "error": f"Người chơi {username1} chưa có bài nộp hợp lệ nào."}

        duel_sub0_id = f"{user0_id}_{sub0['id']}_{sub0['code_hash'][:6]}"
        duel_sub1_id = f"{user1_id}_{sub1['id']}_{sub1['code_hash'][:6]}"

        engine_response = self.engine.run_duel(
            bot0_sub_id=duel_sub0_id, bot0_code=sub0["source_code"], bot0_lang=sub0["language"], bot0_core=core0,
            bot1_sub_id=duel_sub1_id, bot1_code=sub1["source_code"], bot1_lang=sub1["language"], bot1_core=core1,
        )

        if not engine_response.get("success"):
            return {"success": False, "error": engine_response.get("error")}

        match_data = engine_response["data"]
        raw_winner = match_data["winner_id"]
        initial_board = match_data.get("initial_board")
        move_history = match_data.get("move_history", [])

        winner_user_id = user0_id if raw_winner == 0 else (user1_id if raw_winner == 1 else None)
        winner_name = username0 if raw_winner == 0 else (username1 if raw_winner == 1 else "Hòa")
        match_id = f"match_{uuid.uuid4().hex[:12]}"

        # Lưu lịch sử đấu vào SQLite
        self.db.save_match(
            match_id=match_id,
            user0_id=user0_id,
            sub0_id=sub0["id"],
            user1_id=user1_id,
            sub1_id=sub1["id"],
            winner_user_id=winner_user_id,
            reason=match_data.get("reason", "UNKNOWN"),
            bot0_ram=match_data.get("bot0_peak_ram_mb", 0.0),
            bot1_ram=match_data.get("bot1_peak_ram_mb", 0.0),
            replay_data=move_history
        )

        return {
            "success": True,
            "match_id": match_id,
            "initial_board": initial_board,
            "summary": {
                "winner_name": winner_name,
                "winner_slot": raw_winner,
                "reason": match_data.get("reason"),
                "total_rounds": len(move_history),
            },
            "metrics": {
                "player_0": {
                    "username": username0,
                    "language": sub0["language"],
                    "peak_ram_mb": match_data.get("bot0_peak_ram_mb"),
                },
                "player_1": {
                    "username": username1,
                    "language": sub1["language"],
                    "peak_ram_mb": match_data.get("bot1_peak_ram_mb"),
                }
            },
            "replay": move_history
        }

match_service = MatchService()