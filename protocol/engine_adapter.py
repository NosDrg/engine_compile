# engine_adapter.py
import os
import json
import subprocess
from typing import Dict, Any

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class RustEngineAdapter:
    def __init__(self, 
                 engine_bin: str = None,  # type: ignore
                 workspace_dir: str = None,  # type: ignore
                 drivers_dir: str = None): # type: ignore
        
        # Tự động trỏ đúng về project root nếu không truyền vào
        self.engine_bin = os.path.abspath(engine_bin) if engine_bin else os.path.join(BASE_DIR, "target", "release", "match_runner_engine")
        self.workspace_dir = os.path.abspath(workspace_dir) if workspace_dir else os.path.join(BASE_DIR, "workspace")
        self.drivers_dir = os.path.abspath(drivers_dir) if drivers_dir else os.path.join(BASE_DIR, "drivers")

        os.makedirs(self.workspace_dir, exist_ok=True)
        os.makedirs(self.drivers_dir, exist_ok=True)

        # Kiểm tra trước file binary để báo lỗi rõ ràng nếu chưa build
        if not os.path.exists(self.engine_bin):
            raise FileNotFoundError(f"Không tìm thấy file binary tại: {self.engine_bin}. Hãy chạy 'cargo build --release' ở thư mục gốc trước.")
        

    def _get_ext(self, lang: str) -> str:
        return {"python": ".py", "cpp": ".cpp", "java": ".java"}.get(lang.lower(), ".txt")

    def validate_code(self, sub_id: str, source_code: str, lang: str) -> Dict[str, Any]:
        """Gọi CLI: match_runner_engine validate ..."""
        ext = self._get_ext(lang)
        temp_code_file = os.path.join(self.workspace_dir, f"validate_{sub_id}{ext}")

        with open(temp_code_file, "w", encoding="utf-8") as f:
            f.write(source_code)

        try:
            cmd = [
                self.engine_bin,
                "--workspace", self.workspace_dir,
                "--drivers", self.drivers_dir,
                "validate",
                "--sub-id", sub_id,
                "--code-file", temp_code_file,
                "--lang", lang.lower()
            ]

            process = subprocess.run(cmd, capture_output=True, text=True)
            try:
                data = json.loads(process.stdout.strip())
                return data
            except json.JSONDecodeError:
                return {
                    "success": False, 
                    "error": process.stderr.strip() or process.stdout.strip() or "Lỗi gọi CLI Engine"
                }
        finally:
            if os.path.exists(temp_code_file):
                os.remove(temp_code_file)

    def run_duel(self, 
                 bot0_sub_id: str, bot0_code: str, bot0_lang: str, bot0_core: int,
                 bot1_sub_id: str, bot1_code: str, bot1_lang: str, bot1_core: int) -> Dict[str, Any]:
        """Gọi CLI: match_runner_engine duel ..."""
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

            process = subprocess.run(cmd, capture_output=True, text=True)
            stdout_text = process.stdout.strip()

            # Quét từng dòng từ dưới lên để tìm đúng dòng JSON kết quả hợp lệ
            parsed_data = None
            for line in reversed(stdout_text.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        if "success" in data or "data" in data:
                            parsed_data = data
                            break
                    except json.JSONDecodeError:
                        continue

            if parsed_data is not None:
                return parsed_data

            # Nếu không tìm thấy dòng JSON hợp lệ nào
            return {
                "success": False,
                "error": f"Engine Crash: {process.stderr.strip() or stdout_text}"
            }
        finally:
            if os.path.exists(file0): os.remove(file0)
            if os.path.exists(file1): os.remove(file1)