# protocol_service.py
import os
import threading
import uuid
from typing import Dict, Any
from database import DatabaseManager
from engine_adapter import RustEngineAdapter, BASE_DIR

class ProtocolService:
    def __init__(self, 
                 engine_bin: str = None,  # type: ignore
                 db_path: str = None): # type: ignore
        actual_db = db_path if db_path else os.path.join(os.path.dirname(__file__), "match_arena.db")
        self.db = DatabaseManager(db_path=actual_db)
        
        self.engine = RustEngineAdapter(engine_bin=engine_bin)

    def submit_code(self, username: str, language: str, source_code: str) -> Dict[str, Any]:
        """
        Nộp code mới:
        1. Tạo/Lấy user_id.
        2. Chạy validate qua Rust Engine.
        3. Lưu trạng thái và mã băm SHA256 vào SQLite.
        """
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
            return {
                "success": False,
                "submission_id": sub_id,
                "error": err_msg
            }

    def start_match(self, username0: str, username1: str, core0: int = 0, core1: int = 1) -> Dict[str, Any]:
        user0_id = self.db.get_or_create_user(username0)
        user1_id = self.db.get_or_create_user(username1)

        sub0 = self.db.get_latest_valid_submission(user0_id)
        sub1 = self.db.get_latest_valid_submission(user1_id)

        if not sub0:
            return {"success": False, "error": f"Người chơi {username0} chưa có bài nộp hợp lệ nào."}
        if not sub1:
            return {"success": False, "error": f"Người chơi {username1} chưa có bài nộp hợp lệ nào."}

        val0 = self.engine.validate_code(f"pre_{sub0['id']}", sub0["source_code"], sub0["language"])
        val1 = self.engine.validate_code(f"pre_{sub1['id']}", sub1["source_code"], sub1["language"])

        if not val0.get("success") and not val1.get("success"):
            return {
                "success": True,
                "summary": {"winner_name": "Hòa", "winner_slot": None, "reason": "Cả hai bot đều lỗi biên dịch / cú pháp"},
                "metrics": {},
                "replay": []
            }
        if not val0.get("success"):
            return {
                "success": True,
                "summary": {"winner_name": username1, "winner_slot": 1, "reason": f"Bot của {username0} lỗi biên dịch: {val0.get('error')}"},
                "metrics": {},
                "replay": []
            }
        if not val1.get("success"):
            return {
                "success": True,
                "summary": {"winner_name": username0, "winner_slot": 0, "reason": f"Bot của {username1} lỗi biên dịch: {val1.get('error')}"},
                "metrics": {},
                "replay": []
            }
        # -----------------------------------------------------------------

        duel_sub0_id = f"{user0_id}_{sub0['id']}_{sub0['code_hash'][:6]}"
        duel_sub1_id = f"{user1_id}_{sub1['id']}_{sub1['code_hash'][:6]}"

        engine_response = self.engine.run_duel(
            bot0_sub_id=duel_sub0_id, bot0_code=sub0["source_code"], bot0_lang=sub0["language"], bot0_core=core0,
            bot1_sub_id=duel_sub1_id, bot1_code=sub1["source_code"], bot1_lang=sub1["language"], bot1_core=core1,
        )

        if not engine_response.get("success"):
            return {"success": False, "error": engine_response.get("error")}

        match_data = engine_response["data"]
        raw_winner = match_data["winner_id"] # 0, 1 hoặc None

        # Xác định ID người thắng
        winner_user_id = None
        winner_name = "Hòa"
        if raw_winner == 0:
            winner_user_id = user0_id
            winner_name = username0
        elif raw_winner == 1:
            winner_user_id = user1_id
            winner_name = username1

        match_id = f"match_{uuid.uuid4().hex[:12]}"

        # Lưu ván đấu vào SQLite
        self.db.save_match(
            match_id=match_id,
            user0_id=user0_id,
            sub0_id=sub0["id"],
            user1_id=user1_id,
            sub1_id=sub1["id"],
            winner_user_id=winner_user_id,
            reason=match_data["reason"],
            bot0_ram=match_data["bot0_peak_ram_mb"],
            bot1_ram=match_data["bot1_peak_ram_mb"],
            replay_data=match_data["move_history"]
        )

        # Định dạng chuẩn hóa hoàn chỉnh cho Frontend
        return {
            "success": True,
            "match_id": match_id,
            "summary": {
                "winner_name": winner_name,
                "winner_slot": raw_winner,
                "reason": match_data["reason"],
                "total_rounds": len(match_data["move_history"]),
            },
            "metrics": {
                "player_0": {
                    "username": username0,
                    "language": sub0["language"],
                    "peak_ram_mb": match_data["bot0_peak_ram_mb"],
                },
                "player_1": {
                    "username": username1,
                    "language": sub1["language"],
                    "peak_ram_mb": match_data["bot1_peak_ram_mb"],
                }
            },
            "replay": match_data["move_history"]
        }


# --- KỊCH BẢN CHẠY THỬ NGHIỆM ---
if __name__ == "__main__":
    service = ProtocolService()

    # Thí sinh 1 nộp code Python
    py_code = """
def get_move(state):
    return {"from_x": 0, "from_y": 0, "to_x": 0, "to_y": 1}
"""
    print("1. Nộp bài thí sinh 1:")
    res1 = service.submit_code("nguyenvana", "python", py_code)
    print(res1)

    # Thí sinh 2 nộp code C++
    cpp_code = """
#include <nlohmann/json.hpp>
using json = nlohmann::json;

json get_move(const json& state) {
    return {{"from_x", 8, {"from_y", 8}, {"to_x", 8}, {"to_y", 7}};
}
"""
    print("\n2. Nộp bài thí sinh 2:")
    res2 = service.submit_code("tranthib", "cpp", cpp_code)
    print(res2)

    # Tổ chức thi đấu
    print("\n3. Bắt đầu trận đấu:")
    match_result = service.start_match("nguyenvana", "tranthib", core0=0, core1=1)
    
    # In dữ liệu trả về cho Frontend
    import pprint
    pprint.pprint(match_result)


    # Thêm vào ProtocolService trong protocol/protocol_service.py
    def get_match_replay(self, match_id: str) -> Dict[str, Any]:
        match_info = self.db.get_match_by_id(match_id)
        if not match_info:
            return {"success": False, "error": "Không tìm thấy trận đấu"}
        
        return {
            "success": True,
            "match_id": match_info["id"],
            "summary": {
                "winner_name": match_info["winner_name"] or "Hòa",
                "reason": match_info["reason"],
                "created_at": match_info["created_at"]
            },
            "metrics": {
                "player_0": {"username": match_info["user0_name"], "language": match_info["user0_lang"], "peak_ram_mb": match_info["bot0_ram_mb"]},
                "player_1": {"username": match_info["user1_name"], "language": match_info["user1_lang"], "peak_ram_mb": match_info["bot1_ram_mb"]}
            },
            "replay": match_info["replay_data"]
        }


class CoreAllocator:
    def __init__(self):
        # Lấy số core CPU khả dụng trên máy (trừ core 0 cho hệ thống nếu muốn)
        total_cores = os.cpu_count() or 4
        self.available_cores = list(range(total_cores))
        self.lock = threading.Lock()

    def allocate_pair(self):
        with self.lock:
            if len(self.available_cores) >= 2:
                return self.available_cores.pop(0), self.available_cores.pop(0)
            # Nếu hết core thì fallback chia sẻ core 0, 1
            return 0, 1

    def release_pair(self, c1: int, c2: int):
        with self.lock:
            if c1 not in self.available_cores: self.available_cores.append(c1)
            if c2 not in self.available_cores: self.available_cores.append(c2)

    