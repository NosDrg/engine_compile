# protocol/services/matchmaking.py
import asyncio
import logging
from typing import List, Tuple, Optional
from database.db_manager import DatabaseManager
from config import DEFAULT_DB_PATH
from services.match_service import match_service
from core.allocator import core_allocator

logger = logging.getLogger("Matchmaking")

K_FACTOR = 32  # Hệ số nhạy ELO

def calculate_elo(r_a: int, r_b: int, score_a: float) -> Tuple[int, int]:
    """
    Tính điểm ELO mới theo công thức FIDE:
    score_a = 1.0 (A thắng), 0.5 (hòa), 0.0 (B thắng)
    """
    expected_a = 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))
    expected_b = 1.0 - expected_a

    score_b = 1.0 - score_a

    new_r_a = round(r_a + K_FACTOR * (score_a - expected_a))
    new_r_b = round(r_b + K_FACTOR * (score_b - expected_b))

    return max(100, new_r_a), max(100, new_r_b)


class AutoMatchmakingService:
    def __init__(self, db_path: str = DEFAULT_DB_PATH, interval_seconds: int = 180):
        self.db = DatabaseManager(db_path)
        self.interval = interval_seconds
        self.is_running = False

    async def start_loop(self):
        """Vòng lặp chạy ngầm thực thi các trận đấu rank tự động."""
        self.is_running = True
        logger.info(f"Auto-Matchmaking khởi động (chu kỳ {self.interval}s).")
        while self.is_running:
            try:
                await self.run_ladder_round()
            except Exception as e:
                logger.error(f"Lỗi trong vòng đấu tự động: {e}")
            await asyncio.sleep(self.interval)

    def stop(self):
        self.is_running = False

    async def run_ladder_round(self):
        # 1. Lấy danh sách các thí sinh có bot hợp lệ và rating hiện tại
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("""
                SELECT u.id, u.username, COALESCE(u.rating, 1000) as rating
                FROM users u
                WHERE EXISTS (
                    SELECT 1 FROM submissions s 
                    WHERE s.user_id = u.id AND s.status = 'VALID'
                )
                ORDER BY rating ASC
            """).fetchall()

        players = [dict(r) for r in rows]
        if len(players) < 2:
            return

        # 2. Ghép cặp các thí sinh đứng cạnh nhau trên bảng rank (khoảng cách điểm nhỏ nhất)
        pairs: List[Tuple[dict, dict]] = []
        i = 0
        while i < len(players) - 1:
            pairs.append((players[i], players[i + 1]))
            i += 2  # Mỗi thí sinh chỉ đấu tối đa 1 trận mỗi vòng

        # 3. Thực thi lần lượt các cặp đấu
        for p0, p1 in pairs:
            await self._execute_ranked_match(p0, p1)

    async def _execute_ranked_match(self, p0: dict, p1: dict):
        u0_name = p0["username"]
        u1_name = p1["username"]

        c0, c1 = core_allocator.get_pair()
        try:
            # Chạy trận đấu qua Rust Engine
            result = match_service.run_match(u0_name, u1_name, core0=c0, core1=c1)
        finally:
            core_allocator.release_pair(c0, c1)

        if not result.get("success"):
            return

        summary = result.get("summary", {})
        winner_slot = summary.get("winner_slot")  # 0: u0 thắng, 1: u1 thắng, khác: hòa

        if winner_slot == 0:
            score_a = 1.0
        elif winner_slot == 1:
            score_a = 0.0
        else:
            score_a = 0.5

        # Tính toán ELO mới
        old_r0 = p0["rating"]
        old_r1 = p1["rating"]
        new_r0, new_r1 = calculate_elo(old_r0, old_r1, score_a)

        # Cập nhật điểm ELO vào SQLite
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET rating = ? WHERE id = ?", (new_r0, p0["id"]))
            cursor.execute("UPDATE users SET rating = ? WHERE id = ?", (new_r1, p1["id"]))
            conn.commit()

        logger.info(f"[LADDER] {u0_name} ({old_r0}->{new_r0}) vs {u1_name} ({old_r1}->{new_r1}) | Kết quả: Slot {winner_slot}")


matchmaking_engine = AutoMatchmakingService()