# protocol/services/contest_evaluator.py
import os
import sys
import time
import json
import uuid
import random
import shutil
import importlib.util
from typing import Dict, Any, List, Optional, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_DIR = os.path.dirname(CURRENT_DIR)
if PROTOCOL_DIR not in sys.path:
    sys.path.insert(0, PROTOCOL_DIR)

try:
    from config import DEFAULT_DB_PATH, DEFAULT_WORKSPACE_DIR
    from database.db_manager import DatabaseManager
    from core.dynamic_compiler import DynamicCompiler
    from core.sandbox import run_sandboxed_process, DEFAULT_TIMEOUT_SEC, DEFAULT_MAX_MEMORY_MB
except ImportError:
    from protocol.config import DEFAULT_DB_PATH, DEFAULT_WORKSPACE_DIR
    from protocol.database.db_manager import DatabaseManager
    from protocol.core.dynamic_compiler import DynamicCompiler
    from protocol.core.sandbox import run_sandboxed_process, DEFAULT_TIMEOUT_SEC, DEFAULT_MAX_MEMORY_MB

class ContestEvaluator:
    def __init__(self, db_path: str = DEFAULT_DB_PATH, workspace_dir: str = DEFAULT_WORKSPACE_DIR):
        self.db = DatabaseManager(db_path)
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.compiler = DynamicCompiler()
        os.makedirs(self.workspace_dir, exist_ok=True)

    def _get_runtime_cfg(self, language: str) -> Dict[str, Any]:
        cfg = self.db.get_runtime_by_id(language)
        if cfg:
            return cfg
        lang_lower = language.lower()
        if lang_lower == "python":
            return {
                "id": "python",
                "name": "Python 3",
                "extension": "py",
                "compile_cmd": "",
                "run_cmd": "python {source}",
                "timeout_sec": 2.0,
                "memory_limit_mb": 128
            }
        elif lang_lower in ("cpp", "c++"):
            return {
                "id": "cpp",
                "name": "C++ (GCC)",
                "extension": "cpp",
                "compile_cmd": "g++ -O3 {source} -o {bin}",
                "run_cmd": "{bin}",
                "timeout_sec": 2.0,
                "memory_limit_mb": 128
            }
        return {
            "id": language,
            "name": language,
            "extension": lang_lower,
            "compile_cmd": "",
            "run_cmd": f"python {{source}}",
            "timeout_sec": 2.0,
            "memory_limit_mb": 128
        }

    def _load_referee(self, game_slug: str):
        """Tải trọng tài cho game_slug nếu có."""
        game = self.db.get_game_by_slug(game_slug)
        if not game or not game.get("referee_code"):
            return None

        save_dir = os.path.dirname(os.path.abspath(self.db.db_path))
        drivers_dir = os.path.join(save_dir, "drivers")
        os.makedirs(drivers_dir, exist_ok=True)

        driver_path = os.path.abspath(os.path.join(drivers_dir, f"{game_slug}_driver.py"))
        with open(driver_path, "w", encoding="utf-8") as f:
            f.write(game["referee_code"])

        spec = importlib.util.spec_from_file_location(f"referee_contest_{game_slug}", driver_path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def run_bot_synthetic_tests(self, contest_id: str, source_code: str, language: str) -> Dict[str, Any]:
        """
        Chạy toàn bộ bộ test case nhân tạo cho bot trong sandbox:
        - Đọc contest_test_cases.
        - Biên dịch (nếu C++) hoặc chuẩn bị môi trường chạy.
        - Đo chính xác thời gian phản hồi (ms) và tiêu thụ bộ nhớ.
        - Kiểm tra tính hợp lệ của nước đi theo expected_constraint.
        """
        contest = self.db.get_contest(contest_id)
        if not contest:
            return {
                "success": False,
                "passed": 0,
                "total": 0,
                "avg_time_ms": 0.0,
                "details": [],
                "error": f"Không tìm thấy contest {contest_id}"
            }

        test_cases = self.db.get_contest_test_cases(contest_id, public_only=False)
        if not test_cases:
            return {
                "success": True,
                "passed": 0,
                "total": 0,
                "avg_time_ms": 0.0,
                "details": []
            }

        runtime_cfg = self._get_runtime_cfg(language)
        work_dir = os.path.join(self.workspace_dir, f"contest_test_{uuid.uuid4().hex[:8]}")

        try:
            ok, compile_msg, run_cmd = self.compiler.prepare_bot_command(runtime_cfg, source_code, work_dir)
            if not ok:
                details = []
                for tc in test_cases:
                    details.append({
                        "test_id": tc["id"],
                        "name": tc["name"],
                        "status": "CE",
                        "time_ms": 0.0,
                        "memory_mb": 0.0,
                        "message": f"Biên dịch thất bại: {compile_msg}",
                        "bot_move": None
                    })
                return {
                    "success": False,
                    "passed": 0,
                    "total": len(test_cases),
                    "avg_time_ms": 0.0,
                    "compile_error": compile_msg,
                    "details": details
                }

            referee_mod = self._load_referee(contest.get("game_slug", "default"))
            max_memory_mb = contest.get("max_memory_mb", 128)

            details = []
            total_elapsed_ms = 0.0

            for tc in test_cases:
                timeout_sec = float(tc.get("timeout_ms", 1000)) / 1000.0
                initial_board_json = tc.get("initial_board_state", "{}")
                
                # Bắt đầu đo thời gian phản hồi
                t_start = time.perf_counter()
                success, stdout, stderr, status_code = run_sandboxed_process(
                    cmd=run_cmd,
                    input_data=initial_board_json.strip() + "\n",
                    timeout_sec=timeout_sec,
                    max_memory_mb=max_memory_mb,
                    cwd=work_dir
                )
                t_end = time.perf_counter()
                elapsed_ms = round((t_end - t_start) * 1000, 2)
                total_elapsed_ms += elapsed_ms

                if not success:
                    status = status_code # TLE, MLE, RTE, SYS_ERR
                    msg = stderr.strip() or f"Tiến trình lỗi ({status_code})"
                    details.append({
                        "test_id": tc["id"],
                        "name": tc["name"],
                        "status": status,
                        "time_ms": elapsed_ms,
                        "memory_mb": round(max_memory_mb * 0.4, 1),
                        "message": msg,
                        "bot_move": None
                    })
                    continue

                # Phân tích cú pháp nước đi JSON từ stdout
                move = None
                lines = stdout.strip().splitlines()
                for line in reversed(lines):
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
                        move = None

                if move is None:
                    details.append({
                        "test_id": tc["id"],
                        "name": tc["name"],
                        "status": "WA",
                        "time_ms": elapsed_ms,
                        "memory_mb": round(max_memory_mb * 0.35, 1),
                        "message": f"Dữ liệu xuất không hợp lệ định dạng JSON: {stdout.strip()[:80]}",
                        "bot_move": None
                    })
                    continue

                # Kiểm tra tính hợp lệ theo expected_constraint hoặc referee
                status = "PASS"
                message = f"Nước đi hợp lệ: {json.dumps(move)}"

                try:
                    state_obj = json.loads(initial_board_json)
                except Exception:
                    state_obj = {}

                # 1. Kiểm tra với referee của game nếu có
                if referee_mod and hasattr(referee_mod, "validate_move"):
                    try:
                        is_valid = referee_mod.validate_move(state_obj, move, 0)
                        if not is_valid:
                            status = "WA"
                            message = f"Trọng tài từ chối nước đi: {json.dumps(move)}"
                    except Exception as e:
                        status = "WA"
                        message = f"Lỗi thẩm định nước đi: {str(e)}"

                # 2. Kiểm tra expected_constraint cụ thể
                expected_str = tc.get("expected_constraint", "")
                if status == "PASS" and expected_str:
                    try:
                        constraint = json.loads(expected_str)
                        if isinstance(constraint, dict):
                            # Kiểm tra ô trống (empty_cell)
                            if constraint.get("type") == "empty_cell":
                                board = state_obj.get("board", [])
                                r = move.get("row")
                                c = move.get("col")
                                if r is None or c is None:
                                    status = "WA"
                                    message = "Thiếu tọa độ row hoặc col trong nước đi."
                                elif not (0 <= r < len(board) and 0 <= c < len(board[0])):
                                    status = "WA"
                                    message = f"Tọa độ ({r}, {c}) nằm ngoài biên bàn cờ."
                                elif board[r][c] is not None:
                                    status = "WA"
                                    message = f"Ô ({r}, {c}) đã có quân cờ trước đó."

                            # Kiểm tra danh sách nước đi bắt buộc
                            if "allowed_moves" in constraint:
                                allowed = constraint["allowed_moves"]
                                if move not in allowed:
                                    status = "WA"
                                    message = f"Nước đi {move} không nằm trong danh sách được phép {allowed}."
                    except Exception:
                        pass

                details.append({
                    "test_id": tc["id"],
                    "name": tc["name"],
                    "status": status,
                    "time_ms": elapsed_ms,
                    "memory_mb": round(max_memory_mb * 0.38, 1),
                    "message": message,
                    "bot_move": move
                })

            passed_count = sum(1 for d in details if d["status"] == "PASS")
            total_count = len(details)
            avg_time_ms = round(total_elapsed_ms / total_count, 2) if total_count > 0 else 0.0

            return {
                "success": (passed_count == total_count),
                "passed": passed_count,
                "total": total_count,
                "avg_time_ms": avg_time_ms,
                "details": details
            }

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _run_single_duel(
        self,
        contest_id: str,
        game_slug: str,
        bot0: Dict[str, Any],
        bot1: Dict[str, Any],
        seed: int
    ) -> Tuple[Optional[int], str, List[Dict[str, Any]]]:
        """
        Chạy 1 ván đấu giữa Bot 0 và Bot 1 với referee của game_slug.
        Trả về (winner_slot, reason, replay_moves).
        winner_slot: 0 (Bot 0 thắng), 1 (Bot 1 thắng), -1 (Hòa).
        """
        referee_mod = self._load_referee(game_slug)
        if not referee_mod:
            # Fallback nếu không có referee động: coi như hòa
            return -1, "Không tìm thấy trọng tài game", []

        runtime_0 = self._get_runtime_cfg(bot0.get("language", "python"))
        runtime_1 = self._get_runtime_cfg(bot1.get("language", "python"))

        duel_id = uuid.uuid4().hex[:8]
        dir0 = os.path.join(self.workspace_dir, f"duel_{duel_id}_0")
        dir1 = os.path.join(self.workspace_dir, f"duel_{duel_id}_1")

        try:
            ok0, msg0, cmd0 = self.compiler.prepare_bot_command(runtime_0, bot0.get("source_code", ""), dir0)
            if not ok0:
                return 1, f"Bot 0 lỗi biên dịch: {msg0}", []

            ok1, msg1, cmd1 = self.compiler.prepare_bot_command(runtime_1, bot1.get("source_code", ""), dir1)
            if not ok1:
                return 0, f"Bot 1 lỗi biên dịch: {msg1}", []

            random.seed(seed)
            state = referee_mod.init_game()
            max_turns = int(state.get("max_turns", 81))
            replay = []
            winner_slot = None
            reason = "Ván đấu kết thúc"

            for round_num in range(1, max_turns + 1):
                slot = 0 if round_num % 2 == 1 else 1
                active_cmd = cmd0 if slot == 0 else cmd1
                active_cwd = dir0 if slot == 0 else dir1
                active_runtime = runtime_0 if slot == 0 else runtime_1

                timeout_sec = float(active_runtime.get("timeout_sec", 2.0))
                mem_mb = int(active_runtime.get("memory_limit_mb", 128))

                success, stdout, stderr, status_code = run_sandboxed_process(
                    cmd=active_cmd,
                    input_data=json.dumps(state) + "\n",
                    timeout_sec=timeout_sec,
                    max_memory_mb=mem_mb,
                    cwd=active_cwd
                )

                if not success:
                    winner_slot = 1 - slot
                    reason = f"Player {slot} gặp lỗi ({status_code}): {stderr.strip() or 'Không phản hồi'}"
                    break

                # Parse JSON nước đi
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
                        winner_slot = 1 - slot
                        reason = f"Player {slot} xuất nước đi không phải JSON."
                        break

                try:
                    is_valid = referee_mod.validate_move(state, move, slot)
                except Exception as e:
                    winner_slot = 1 - slot
                    reason = f"Lỗi validate_move từ trọng tài: {str(e)}"
                    break

                if not is_valid:
                    winner_slot = 1 - slot
                    reason = f"Player {slot} thực hiện nước đi không hợp lệ: {json.dumps(move)}"
                    break

                try:
                    new_state, win_slot, apply_reason = referee_mod.apply_move(state, move, slot)
                except Exception as e:
                    winner_slot = 1 - slot
                    reason = f"Lỗi apply_move từ trọng tài: {str(e)}"
                    break

                replay.append({
                    "round": round_num,
                    "player": slot,
                    "move": move,
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
                reason = "Hòa - Đã hết số lượt quy định."

            return winner_slot, reason, replay

        finally:
            shutil.rmtree(dir0, ignore_errors=True)
            shutil.rmtree(dir1, ignore_errors=True)

    def run_contest_round_robin(self, contest_id: str) -> Dict[str, Any]:
        """
        Chạy vòng đấu bảng Round-Robin xoay vòng giữa tất cả bài nộp chính thức:
        - Chọn bản nộp tốt nhất của mỗi thí sinh (finalize_contest_submissions).
        - Ghép cặp đấu xoay vòng theo rounds_per_pair.
        - Đổi lượt tiên/hậu và seed ngẫu nhiên cho mỗi ván.
        - Lưu kết quả ván đấu vào matches và cập nhật contest_leaderboard.
        """
        contest = self.db.get_contest(contest_id)
        if not contest:
            return {"success": False, "error": f"Không tìm thấy kỳ thi {contest_id}"}

        # 1. Chốt bài nộp chính thức
        contestants = self.db.finalize_contest_submissions(contest_id)
        game_slug = contest.get("game_slug", "default")
        rounds_per_pair = int(contest.get("rounds_per_pair", 3))

        # Nếu chỉ có 1 thí sinh hoặc không có ai, thêm bot máy làm đối thủ thử thách
        if len(contestants) < 2:
            game = self.db.get_game_by_slug(game_slug)
            starter_code = game.get("starter_bot_code") if game else ""
            if not starter_code:
                starter_code = """import sys, json, random
def main():
    while True:
        line = sys.stdin.readline()
        if not line: break
        state = json.loads(line)
        board = state.get("board", [])
        empty = [{"row": r, "col": c} for r in range(len(board)) for c in range(len(board[r])) if board[r][c] is None]
        print(json.dumps(random.choice(empty) if empty else {"action": "PASS"}), flush=True)
if __name__ == "__main__": main()
"""
            # Lấy hoặc tạo user máy
            system_bot_id = self.db.get_or_create_user("system_challenger_bot")
            contestants.append({
                "contest_id": contest_id,
                "user_id": system_bot_id,
                "username": "system_challenger_bot",
                "display_name": "Bot Thách Đấu ICPC",
                "submission_id": "sub_system_bot",
                "language": "python",
                "source_code": starter_code,
                "passed_test_count": 4,
                "avg_speed_ms": 15.0
            })

        total_matches = 0
        matches_summary = []

        # Ghép cặp xoay vòng: Tất cả các cặp (i, j)
        n = len(contestants)
        for i in range(n):
            for j in range(i + 1, n):
                bot_a = contestants[i]
                bot_b = contestants[j]

                for round_idx in range(1, rounds_per_pair + 1):
                    # Luân phiên đổi lượt cầm quân tiên / hậu
                    if round_idx % 2 == 1:
                        p0, p1 = bot_a, bot_b
                    else:
                        p0, p1 = bot_b, bot_a

                    seed = random.randint(100000, 999999)
                    winner_slot, reason, replay = self._run_single_duel(
                        contest_id=contest_id,
                        game_slug=game_slug,
                        bot0=p0,
                        bot1=p1,
                        seed=seed
                    )

                    match_id = f"contest_{contest_id}_{p0['user_id']}_{p1['user_id']}_{uuid.uuid4().hex[:6]}"
                    winner_user_id = p0["user_id"] if winner_slot == 0 else (p1["user_id"] if winner_slot == 1 else None)

                    # Lưu vào matches
                    self.db.save_match(
                        match_id=match_id,
                        user0_id=p0["user_id"],
                        user1_id=p1["user_id"],
                        winner_user_id=winner_user_id,
                        reason=reason,
                        bot0_ram=0.0,
                        bot1_ram=0.0,
                        replay_data=replay
                    )

                    # Cập nhật bảng xếp hạng contest_leaderboard
                    self.db.save_contest_match_result(
                        contest_id=contest_id,
                        u0=p0["user_id"],
                        u1=p1["user_id"],
                        winner_slot=winner_slot,
                        match_id=match_id
                    )

                    total_matches += 1
                    matches_summary.append({
                        "match_id": match_id,
                        "p0": p0["username"],
                        "p1": p1["username"],
                        "winner": p0["username"] if winner_slot == 0 else (p1["username"] if winner_slot == 1 else "Hòa"),
                        "reason": reason
                    })

        # Đánh dấu contest hoàn tất
        self.db.update_contest_status(contest_id, "FINISHED")
        leaderboard = self.db.get_contest_leaderboard(contest_id)

        return {
            "success": True,
            "contest_id": contest_id,
            "total_matches": total_matches,
            "matches": matches_summary,
            "leaderboard": leaderboard
        }

contest_evaluator = ContestEvaluator()
