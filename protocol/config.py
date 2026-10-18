import os
from pathlib import Path

# Thư mục protocol/
PROTOCOL_DIR = Path(__file__).resolve().parent

# Thư mục gốc dự án (/app trên container hoặc thư mục root repo)
ROOT_DIR = PROTOCOL_DIR.parent

# 1. Cơ sở dữ liệu SQLite trong thư mục save/
DEFAULT_DB_PATH = str(PROTOCOL_DIR / "save" / "match_arena.db")

# 2. Đường dẫn file thực thi Rust engine đã build
DEFAULT_ENGINE_BIN = str(ROOT_DIR / "target" / "release" / "match_runner_engine")

# 3. Thư mục sandbox chứa mã nguồn chạy tạm của bot
DEFAULT_WORKSPACE_DIR = str(ROOT_DIR / "workspace")
WORKSPACE_DIR = DEFAULT_WORKSPACE_DIR

# 4. Thư mục chứa các driver giao tiếp với bot
DEFAULT_DRIVERS_DIR = str(ROOT_DIR / "drivers")

# 5. Thư mục giao diện tĩnh
FRONTEND_DIR = str(ROOT_DIR / "frontend")