import json
import shutil
import importlib.util
from core.dynamic_compiler import DynamicCompiler
from core.sandbox import run_sandboxed_process
# protocol/services/match_service.py
import os
import uuid
from typing import Dict, Any, Optional
from config import DEFAULT_ENGINE_BIN, DEFAULT_WORKSPACE_DIR, DEFAULT_DRIVERS_DIR, DEFAULT_DB_PATH
from database.db_manager import DatabaseManager
from engine.adapter import RustEngineAdapter

# Định nghĩa bot mẫu phục vụ chế độ đấu thử (Practice Mode)
PRACTICE_BOTS = {
    "random_bot": {
        "name": "RandomBot (Máy)",
        "language": "python",
        "code": """import sys
import json
import random

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            data = json.loads(line.strip())
            valid_moves = data.get("valid_moves", [])
            if valid_moves:
                move = random.choice(valid_moves)
                print(json.dumps(move), flush=True)
            else:
                print(json.dumps({"action": "PASS"}), flush=True)
        except Exception:
            print(json.dumps({"action": "PASS"}), flush=True)

if __name__ == "__main__":
    main()
"""
    },
    "greedy_bot": {
        "name": "GreedyBot (Máy)",
        "language": "python",
        "code": """import sys
import json

def score_move(move):
    if move.get("is_capture"):
        return 100
    if move.get("to_base"):
        return 50
    return 1

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            data = json.loads(line.strip())
            valid_moves = data.get("valid_moves", [])
            if valid_moves:
                best_move = max(valid_moves, key=score_move)
                print(json.dumps(best_move), flush=True)
            else:
                print(json.dumps({"action": "PASS"}), flush=True)
        except Exception:
            print(json.dumps({"action": "PASS"}), flush=True)

if __name__ == "__main__":
    main()
"""
    }
}


class MatchService:
    def __init__(self,
                 engine_bin: str = DEFAULT_ENGINE_BIN,
                 workspace_dir: str = DEFAULT_WORKSPACE_DIR,
                 drivers_dir: str = DEFAULT_DRIVERS_DIR,
                 db_path: str = DEFAULT_DB_PATH):
        self.db = DatabaseManager(db_path)
        self.engine = RustEngineAdapter(engine_bin, workspace_dir, drivers_dir)
        self.drivers_dir = drivers_dir
        self.workspace_dir = workspace_dir
        self.compiler = DynamicCompiler()

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
            user0_lang=sub0["language"],
            sub0_code_hash=sub0["code_hash"],
            sub0_id=sub0["id"],
            user1_id=user1_id,
            user1_lang=sub1["language"],
            sub1_code_hash=sub1["code_hash"],
            sub1_id=sub1["id"],
            winner_user_id=winner_user_id,
            reason=match_data.get("reason", "UNKNOWN"),
            bot0_ram_mb=match_data.get("bot0_peak_ram_mb", 0.0),
            bot1_ram_mb=match_data.get("bot1_peak_ram_mb", 0.0),
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


    def prepare_dynamic_referee_driver(self, game_slug: str) -> str:
        """
        Lấy thông tin game_slug từ database và lưu mã referee_code thành file driver
        tại protocol/save/drivers/{game_slug}_driver.py, sau đó trả về đường dẫn tuyệt đối.
        """
        game = self.db.get_game_by_slug(game_slug)
        if not game or not game.get("referee_code"):
            raise ValueError(f"Không tìm thấy cấu hình hoặc referee_code của game '{game_slug}'.")

        save_dir = os.path.dirname(os.path.abspath(self.db.db_path))
        drivers_dir = os.path.join(save_dir, "drivers")
        os.makedirs(drivers_dir, exist_ok=True)

        driver_path = os.path.abspath(os.path.join(drivers_dir, f"{game_slug}_driver.py"))
        with open(driver_path, "w", encoding="utf-8") as f:
            f.write(game["referee_code"])

        return driver_path

    def run_practice_session(
        self,
        username: str,
        language: str,
        source_code: str,
        bot_type: str = "random_bot",
        game_slug: str = "default"
    ) -> Dict[str, Any]:
        """
        Chế độ chạy thử / luyện tập:
        - Nạp referee của game_slug tương ứng từ database để chạy phiên đấu thử nghiệm.
        - Tương thích ngược: Nếu game_slug là default và chưa có referee code, chuyển tiếp cho Rust engine.
        - Trả về replay và dữ liệu trận đấu ngay lập tức mà KHÔNG ghi vào bảng xếp hạng SQLite.
        """
        # Kiểm tra game trong CSDL
        game = self.db.get_game_by_slug(game_slug)
        has_dynamic_referee = bool(game and game.get("referee_code"))

        # Nếu có referee động, chạy thông qua Dynamic Game Engine
        if has_dynamic_referee:
            try:
                driver_path = self.prepare_dynamic_referee_driver(game_slug)
                spec = importlib.util.spec_from_file_location(f"referee_{game_slug}", driver_path)
                if not spec or not spec.loader:
                    return {"success": False, "error": f"Không thể nạp driver trọng tài cho '{game_slug}'"}
                referee_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(referee_mod)
            except Exception as e:
                return {"success": False, "error": f"Lỗi khởi tạo trọng tài: {str(e)}"}

            # Kiểm tra 3 hàm bắt buộc theo giao thức
            for fn in ["init_game", "validate_move", "apply_move"]:
                if not hasattr(referee_mod, fn) or not callable(getattr(referee_mod, fn)):
                    return {"success": False, "error": f"Trọng tài game '{game_slug}' thiếu hàm bắt buộc '{fn}'"}

            # Chuẩn bị môi trường chạy bot cho Player 0
            runtime_0 = self.db.get_runtime_by_id(language) or {
                "id": language,
                "name": language,
                "extension": "py" if language.lower() == "python" else language.lower(),
                "compile_cmd": "" if language.lower() == "python" else "g++ -O3 {source} -o {bin}",
                "run_cmd": "python {source}" if language.lower() == "python" else "{bin}",
                "timeout_sec": 2.0,
                "memory_limit_mb": 128
            }

            practice_id = uuid.uuid4().hex[:8]
            work_dir_0 = os.path.abspath(os.path.join(self.workspace_dir, f"prac_{practice_id}_p0"))
            work_dir_1 = os.path.abspath(os.path.join(self.workspace_dir, f"prac_{practice_id}_p1"))

            try:
                # Compile / chuẩn bị lệnh player 0
                ok0, msg0, cmd0 = self.compiler.prepare_bot_command(runtime_0, source_code, work_dir_0)
                if not ok0:
                    return {"success": False, "error": msg0}

                # Chuẩn bị đối thủ máy Player 1
                opponent_name = "Bot Máy"
                opponent_lang = "python"
                if game and game.get("starter_bot_code"):
                    opponent_code = game["starter_bot_code"]
                    opponent_name = f"Bot Mẫu ({game['name']})"
                else:
                    bot_meta = PRACTICE_BOTS.get(bot_type, PRACTICE_BOTS["random_bot"])
                    opponent_name = bot_meta["name"]
                    opponent_lang = bot_meta["language"]
                    opponent_code = bot_meta["code"]

                runtime_1 = self.db.get_runtime_by_id(opponent_lang) or {
                    "id": opponent_lang,
                    "name": opponent_lang,
                    "extension": "py",
                    "compile_cmd": "",
                    "run_cmd": "python {source}",
                    "timeout_sec": 2.0,
                    "memory_limit_mb": 128
                }

                ok1, msg1, cmd1 = self.compiler.prepare_bot_command(runtime_1, opponent_code, work_dir_1)
                if not ok1:
                    return {"success": False, "error": f"Lỗi chuẩn bị bot đối thủ: {msg1}"}

                # Khởi tạo trận đấu qua trọng tài
                state = referee_mod.init_game()
                initial_board = state.get("board", state)
                move_history = []
                winner_slot = None
                reason = "Trận đấu kết thúc"
                max_rounds = int(state.get("max_turns", 80))

                for round_num in range(1, max_rounds + 1):
                    # Lượt của ai: mặc định xen kẽ P0, P1
                    current_slot = 0 if round_num % 2 == 1 else 1
                    active_cmd = cmd0 if current_slot == 0 else cmd1
                    active_cwd = work_dir_0 if current_slot == 0 else work_dir_1
                    active_runtime = runtime_0 if current_slot == 0 else runtime_1

                    t_sec = float(active_runtime.get("timeout_sec") or 2.0)
                    m_mb = int(active_runtime.get("memory_limit_mb") or 128)

                    # Gửi trạng thái qua stdin
                    success, stdout, stderr, status_code = run_sandboxed_process(
                        cmd=active_cmd,
                        input_data=json.dumps(state) + "\n",
                        timeout_sec=t_sec,
                        max_memory_mb=m_mb,
                        cwd=active_cwd
                    )

                    if not success:
                        winner_slot = 1 - current_slot
                        reason = f"Player {current_slot} bị lỗi ({status_code}): {stderr.strip() or 'Không phản hồi'}"
                        break

                    # Phân tích cú pháp nước đi JSON từ stdout
                    move = None
                    for line in reversed(stdout.strip().splitlines()):
                        line = line.strip()
                        if line.startswith("{") and line.endswith("}"):
                            try:
                                move = json.loads(line)
                                break
                            except Exception:
                                continue
                    if move is None:
                        try:
                            move = json.loads(stdout.strip())
                        except Exception:
                            winner_slot = 1 - current_slot
                            reason = f"Player {current_slot} trả về nước đi không đúng JSON: {stdout.strip()[:100]}"
                            break

                    # Kiểm tra tính hợp lệ của nước đi
                    try:
                        is_valid = referee_mod.validate_move(state, move, current_slot)
                    except Exception as e:
                        winner_slot = 1 - current_slot
                        reason = f"Trọng tài phát sinh lỗi validate_move: {str(e)}"
                        break

                    if not is_valid:
                        winner_slot = 1 - current_slot
                        reason = f"Player {current_slot} thực hiện nước đi không hợp lệ: {json.dumps(move)}"
                        break

                    # Áp dụng nước đi
                    try:
                        new_state, win_slot, apply_reason = referee_mod.apply_move(state, move, current_slot)
                    except Exception as e:
                        winner_slot = 1 - current_slot
                        reason = f"Trọng tài phát sinh lỗi apply_move: {str(e)}"
                        break

                    move_history.append({
                        "round": round_num,
                        "player": current_slot,
                        "move": move,
                        "move_obj": move,
                        "state": new_state,
                        "reason": apply_reason
                    })

                    state = new_state
                    if win_slot is not None:
                        winner_slot = win_slot
                        reason = apply_reason
                        break

                if winner_slot is None:
                    winner_slot = -1
                    reason = "Hòa - Đã hết số lượt đấu quy định."

                winner_name = username if winner_slot == 0 else (opponent_name if winner_slot == 1 else "Hòa")
                practice_match_id = f"practice_{uuid.uuid4().hex[:10]}"

                return {
                    "success": True,
                    "is_practice": True,
                    "match_id": practice_match_id,
                    "initial_board": initial_board,
                    "summary": {
                        "winner_name": winner_name,
                        "winner_slot": winner_slot,
                        "reason": reason,
                        "total_rounds": len(move_history),
                    },
                    "metrics": {
                        "player_0": {
                            "username": username,
                            "language": language,
                            "peak_ram_mb": 0.0,
                        },
                        "player_1": {
                            "username": opponent_name,
                            "language": opponent_lang,
                            "peak_ram_mb": 0.0,
                        }
                    },
                    "replay": move_history
                }

            finally:
                shutil.rmtree(work_dir_0, ignore_errors=True)
                shutil.rmtree(work_dir_1, ignore_errors=True)

        # Fallback cho Rust Engine nếu game_slug là default và không có referee động
        val_result = self.validate_code_only(source_code, language)
        if not val_result.get("success"):
            return {
                "success": False,
                "error": f"Lỗi biên dịch / cú pháp: {val_result.get('error', 'Không xác định')}"
            }

        bot_meta = PRACTICE_BOTS.get(bot_type, PRACTICE_BOTS["random_bot"])
        opponent_name = bot_meta["name"]
        opponent_lang = bot_meta["language"]
        opponent_code = bot_meta["code"]

        driver_file = os.path.join(self.drivers_dir, f"{bot_type}.py")
        if os.path.exists(driver_file):
            try:
                with open(driver_file, "r", encoding="utf-8") as f:
                    opponent_code = f.read()
            except Exception:
                pass

        try:
            from core.allocator import core_allocator
            c0, c1 = core_allocator.get_pair()
            has_allocator = True
        except Exception:
            c0, c1 = 0, 1
            has_allocator = False

        practice_user_sub_id = f"prac_{uuid.uuid4().hex[:8]}"
        practice_bot_sub_id = f"bot_{uuid.uuid4().hex[:8]}"

        try:
            engine_response = self.engine.run_duel(
                bot0_sub_id=practice_user_sub_id,
                bot0_code=source_code,
                bot0_lang=language,
                bot0_core=c0,
                bot1_sub_id=practice_bot_sub_id,
                bot1_code=opponent_code,
                bot1_lang=opponent_lang,
                bot1_core=c1,
            )
        finally:
            if has_allocator:
                core_allocator.release_pair(c0, c1)

        if not engine_response.get("success"):
            return {"success": False, "error": engine_response.get("error")}

        match_data = engine_response["data"]
        raw_winner = match_data["winner_id"]
        initial_board = match_data.get("initial_board")
        move_history = match_data.get("move_history", [])

        winner_name = username if raw_winner == 0 else (opponent_name if raw_winner == 1 else "Hòa")
        practice_match_id = f"practice_{uuid.uuid4().hex[:10]}"

        return {
            "success": True,
            "is_practice": True,
            "match_id": practice_match_id,
            "initial_board": initial_board,
            "summary": {
                "winner_name": winner_name,
                "winner_slot": raw_winner,
                "reason": match_data.get("reason"),
                "total_rounds": len(move_history),
            },
            "metrics": {
                "player_0": {
                    "username": username,
                    "language": language,
                    "peak_ram_mb": match_data.get("bot0_peak_ram_mb"),
                },
                "player_1": {
                    "username": opponent_name,
                    "language": opponent_lang,
                    "peak_ram_mb": match_data.get("bot1_peak_ram_mb"),
                }
            },
            "replay": move_history
        }


match_service = MatchService()
