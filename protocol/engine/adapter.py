# protocol/engine/adapter.py
import os
import json
import subprocess
from typing import Dict, Any

class RustEngineAdapter:
    def __init__(self, engine_bin: str, workspace_dir: str, drivers_dir: str):
        self.engine_bin = os.path.abspath(engine_bin)
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.drivers_dir = os.path.abspath(drivers_dir)

        os.makedirs(self.workspace_dir, exist_ok=True)
        os.makedirs(self.drivers_dir, exist_ok=True)

        if not os.path.exists(self.engine_bin):
            raise FileNotFoundError(
                f"Không tìm thấy binary Engine tại: {self.engine_bin}. Hãy chạy 'cargo build --release' trước."
            )

    def _get_ext(self, lang: str) -> str:
        return {"python": ".py", "cpp": ".cpp", "java": ".java"}.get(lang.lower(), ".txt")

    def validate_code(self, sub_id: str, source_code: str, lang: str) -> Dict[str, Any]:
        ext = self._get_ext(lang)
        temp_file = os.path.join(self.workspace_dir, f"validate_{sub_id}{ext}")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(source_code)

        try:
            cmd = [
                self.engine_bin,
                "--workspace", self.workspace_dir,
                "--drivers", self.drivers_dir,
                "validate",
                "--sub-id", sub_id,
                "--code-file", temp_file,
                "--lang", lang.lower()
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            for line in reversed(proc.stdout.strip().splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
            return {"success": False, "error": proc.stderr.strip() or proc.stdout.strip() or "Lỗi validate"}
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def run_duel(self, 
                 bot0_sub_id: str, bot0_code: str, bot0_lang: str, bot0_core: int,
                 bot1_sub_id: str, bot1_code: str, bot1_lang: str, bot1_core: int) -> Dict[str, Any]:
        file0 = os.path.join(self.workspace_dir, f"bot0_{bot0_sub_id}{self._get_ext(bot0_lang)}")
        file1 = os.path.join(self.workspace_dir, f"bot1_{bot1_sub_id}{self._get_ext(bot1_lang)}")

        with open(file0, "w", encoding="utf-8") as f:
            f.write(bot0_code)
        with open(file1, "w", encoding="utf-8") as f:
            f.write(bot1_code)

        try:
            cmd = [
                self.engine_bin,
                "--workspace", self.workspace_dir,
                "--drivers", self.drivers_dir,
                "duel",
                "--bot0-id", bot0_sub_id,
                "--bot0-code-file", file0,
                "--bot0-lang", bot0_lang.lower(),
                "--bot0-core", str(bot0_core),
                "--bot1-id", bot1_sub_id,
                "--bot1-code-file", file1,
                "--bot1-lang", bot1_lang.lower(),
                "--bot1-core", str(bot1_core),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            for line in reversed(proc.stdout.strip().splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        if "success" in data or "data" in data:
                            return data
                    except json.JSONDecodeError:
                        continue
            return {"success": False, "error": f"Engine Crash: {proc.stderr.strip() or proc.stdout.strip()}"}
        finally:
            if os.path.exists(file0): os.remove(file0)
            if os.path.exists(file1): os.remove(file1)