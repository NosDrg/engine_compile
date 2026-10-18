import os
from pathlib import Path

# Thư mục protocol/
PROTOCOL_DIR = Path(__file__).resolve().parent

# Thư mục gốc project (/app hoặc repo root)
ROOT_DIR = PROTOCOL_DIR.parent

# Đường dẫn database tuyệt đối nằm ngay trong protocol/
DEFAULT_DB_PATH = str(PROTOCOL_DIR / "save" / "match_arena.db")

# Đường dẫn thư mục frontend
FRONTEND_DIR = str(ROOT_DIR / "frontend")

# Thư mục sandbox cho engine
WORKSPACE_DIR = str(ROOT_DIR / "workspace")