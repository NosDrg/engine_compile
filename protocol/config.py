# protocol/config.py
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# Thư mục chứa Binary Rust Engine
DEFAULT_ENGINE_BIN = os.path.join(PROJECT_ROOT, "target", "release", "match_runner_engine")
DEFAULT_WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")
DEFAULT_DRIVERS_DIR = os.path.join(PROJECT_ROOT, "drivers")
DEFAULT_DB_PATH = os.path.join(CURRENT_DIR, "save/match_arena.db")

# Thư mục Frontend
if os.path.isdir(os.path.join(PROJECT_ROOT, "frontend")):
    FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
elif os.path.isdir(os.path.join(CURRENT_DIR, "frontend")):
    FRONTEND_DIR = os.path.join(CURRENT_DIR, "frontend")
else:
    FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")