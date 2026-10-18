# protocol/core/allocator.py
import os
import threading
from typing import Tuple

class CoreManager:
    """Quản lý phân phối tài nguyên CPU core để cách ly 2 bot khi giao đấu."""
    def __init__(self):
        total_cores = os.cpu_count() or 4
        self.available_cores = list(range(total_cores))
        self.lock = threading.Lock()

    def get_pair(self) -> Tuple[int, int]:
        with self.lock:
            if len(self.available_cores) >= 2:
                return self.available_cores.pop(0), self.available_cores.pop(0)
            return 0, 1

    def release_pair(self, c1: int, c2: int) -> None:
        with self.lock:
            if c1 not in self.available_cores:
                self.available_cores.append(c1)
            if c2 not in self.available_cores:
                self.available_cores.append(c2)

core_allocator = CoreManager()