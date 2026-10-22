# protocol/core/sandbox.py
import os
import sys
import subprocess
from typing import Tuple, Optional

# Kiểm tra nền tảng để tránh lỗi linting trên Windows
if sys.platform != "win32":
    import resource
else:
    resource = None  # type: ignore

DEFAULT_TIMEOUT_SEC = 2.0
DEFAULT_MAX_MEMORY_MB = 128
DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024

def set_sandbox_limits(max_memory_mb: int = DEFAULT_MAX_MEMORY_MB):
    """Áp đặt giới hạn tài nguyên Linux Kernel (bỏ qua nếu chạy thử trên Windows)."""
    if not resource:
        return

    setrlimit = getattr(resource, "setrlimit", None)
    if not callable(setrlimit):
        return

    rlimit_as = getattr(resource, "RLIMIT_AS", None)
    rlimit_nproc = getattr(resource, "RLIMIT_NPROC", None)
    rlimit_fsize = getattr(resource, "RLIMIT_FSIZE", None)
    rlimit_cpu = getattr(resource, "RLIMIT_CPU", None)
    res_error = getattr(resource, "error", Exception)

    # 1. Giới hạn RAM
    mem_bytes = max_memory_mb * 1024 * 1024
    if rlimit_as is not None:
        try:
            setrlimit(rlimit_as, (mem_bytes, mem_bytes))
        except (ValueError, res_error):
            pass

    # 2. Giới hạn tạo tiến trình con (Fork bomb)
    if rlimit_nproc is not None:
        try:
            setrlimit(rlimit_nproc, (1, 1))
        except (ValueError, res_error):
            pass

    # 3. Chặn ghi file ra đĩa
    if rlimit_fsize is not None:
        try:
            setrlimit(rlimit_fsize, (0, 0))
        except (ValueError, res_error):
            pass

    # 4. Giới hạn CPU time
    if rlimit_cpu is not None:
        try:
            setrlimit(rlimit_cpu, (int(DEFAULT_TIMEOUT_SEC) + 1, int(DEFAULT_TIMEOUT_SEC) + 1))
        except (ValueError, res_error):
            pass


def run_sandboxed_process(
    cmd: list,
    input_data: str = "",
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB,
    cwd: Optional[str] = None
) -> Tuple[bool, str, str, str]:
    try:
        extra_kwargs = {}
        if sys.platform != "win32":
            extra_kwargs["preexec_fn"] = lambda: set_sandbox_limits(max_memory_mb)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            **extra_kwargs
        )

        stdout, stderr = proc.communicate(input=input_data, timeout=timeout_sec)
        stdout = stdout[:DEFAULT_MAX_OUTPUT_BYTES]
        stderr = stderr[:DEFAULT_MAX_OUTPUT_BYTES]

        if proc.returncode == 0:
            return True, stdout, stderr, "SUCCESS"
        elif proc.returncode in (-9, 137):
            return False, stdout, "Bộ nhớ vượt quá giới hạn cho phép (Memory Limit Exceeded).", "MLE"
        else:
            return False, stdout, stderr or f"Tiến trình dừng với mã {proc.returncode}.", "RTE"

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return False, "", f"Hết thời gian phản hồi (quá {timeout_sec}s).", "TLE"
    except Exception as e:
        return False, "", f"Lỗi thực thi sandbox: {str(e)}", "SYS_ERR"
