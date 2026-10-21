# protocol/core/dynamic_compiler.py
import os
import sys
import shlex
from typing import Tuple, List, Dict, Any
from core.sandbox import run_sandboxed_process, DEFAULT_TIMEOUT_SEC, DEFAULT_MAX_MEMORY_MB


class DynamicCompiler:
    """
    Điều phối việc ghi file, biên dịch và chuẩn bị lệnh thực thi (execution command)
    cho bot dựa trên cấu hình runtime động (Python, C++, Go, Node.js,...).
    """

    def prepare_bot_command(
        self,
        runtime_cfg: Dict[str, Any],
        source_code: str,
        work_dir: str
    ) -> Tuple[bool, str, List[str]]:
        """
        Thực hiện chuẩn bị file và lệnh chạy cho bot:
        1. Ghi mã nguồn source_code ra đĩa theo extension chỉ định.
        2. Nếu runtime có compile_cmd: thực thi lệnh biên dịch trong môi trường sandbox an toàn.
        3. Format run_cmd để chuẩn bị danh sách tham số khởi chạy bot.
        """
        try:
            work_dir = os.path.abspath(work_dir)
            os.makedirs(work_dir, exist_ok=True)

            ext = str(runtime_cfg.get("extension", "txt")).lstrip(".")
            source_filename = f"bot.{ext}"
            source_file = os.path.join(work_dir, source_filename)

            # 1. Ghi mã nguồn ra file đĩa
            with open(source_file, "w", encoding="utf-8") as f:
                f.write(source_code)

            # Xác định đường dẫn file thực thi (binary) nếu cần biên dịch
            bin_name = "bot.exe" if sys.platform == "win32" else "bot.bin"
            bin_file = os.path.join(work_dir, bin_name)

            # Các biến thay thế định dạng đường dẫn
            placeholders = {
                "source": source_file.replace("\\", "/"),
                "bin": bin_file.replace("\\", "/"),
                "work_dir": work_dir.replace("\\", "/")
            }

            compile_cmd = (runtime_cfg.get("compile_cmd") or "").strip()
            timeout_sec = float(runtime_cfg.get("timeout_sec") or DEFAULT_TIMEOUT_SEC)
            memory_limit_mb = int(runtime_cfg.get("memory_limit_mb") or DEFAULT_MAX_MEMORY_MB)

            # 2. Nếu có compile_cmd: thực hiện biên dịch
            if compile_cmd:
                formatted_compile = compile_cmd.format(**placeholders)
                is_posix = (sys.platform != "win32")
                compile_args = shlex.split(formatted_compile, posix=is_posix)

                # Dành thời gian biên dịch rộng rãi hơn runtime bình thường (tối thiểu 10s hoặc timeout_sec * 3)
                compile_timeout = max(10.0, timeout_sec * 3)
                compile_mem = max(256, memory_limit_mb * 2)

                success, stdout, stderr, status_code = run_sandboxed_process(
                    cmd=compile_args,
                    input_data="",
                    timeout_sec=compile_timeout,
                    max_memory_mb=compile_mem,
                    cwd=work_dir
                )

                if not success:
                    err_msg = stderr.strip() or stdout.strip() or f"Biên dịch thất bại với mã lỗi {status_code}"
                    return False, f"Compile Error:\n{err_msg}", []

            # 3. Format run_cmd và trả về command list
            run_cmd = (runtime_cfg.get("run_cmd") or "").strip()
            if not run_cmd:
                return False, "Cấu hình runtime thiếu run_cmd.", []

            formatted_run = run_cmd.format(**placeholders)
            is_posix = (sys.platform != "win32")
            run_args = shlex.split(formatted_run, posix=is_posix)

            return True, "OK", run_args

        except Exception as e:
            return False, f"Lỗi hệ thống khi chuẩn bị bot: {str(e)}", []
