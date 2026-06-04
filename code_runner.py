"""
TutorFlow 代码执行器

在隔离的子进程中运行用户代码，捕获 stdout/stderr，
支持超时控制和安全的执行环境。
"""

import subprocess
import tempfile
import os
import sys
from typing import NamedTuple


class RunResult(NamedTuple):
    """代码执行结果"""
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    elapsed_ms: float


def run_python_code(code: str, timeout: int = 30) -> RunResult:
    """
    在子进程中安全执行 Python 代码。

    Args:
        code:  要执行的 Python 源代码
        timeout: 超时秒数（默认 30）

    Returns:
        RunResult 包含 stdout, stderr, exit_code, timed_out, elapsed_ms
    """
    if not code.strip():
        return RunResult(
            stdout="",
            stderr="⚠️ 代码为空，请输入代码后再运行。",
            exit_code=-1,
            timed_out=False,
            elapsed_ms=0,
        )

    # 写入临时文件，确保语法完整的代码能被正确执行
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name
    except OSError as e:
        return RunResult(
            stdout="",
            stderr=f"无法创建临时文件: {e}",
            exit_code=-1,
            timed_out=False,
            elapsed_ms=0,
        )

    try:
        import time
        start = time.perf_counter()

        # 使用与当前环境相同的 Python 解释器
        python_exe = sys.executable

        proc = subprocess.Popen(
            [python_exe, tmp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=os.path.dirname(tmp_path),
        )

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            timed_out = True

        elapsed = (time.perf_counter() - start) * 1000

        return RunResult(
            stdout=stdout or "",
            stderr=stderr or "",
            exit_code=proc.returncode,
            timed_out=timed_out,
            elapsed_ms=elapsed,
        )

    except Exception as e:
        return RunResult(
            stdout="",
            stderr=f"执行异常: {e}",
            exit_code=-1,
            timed_out=False,
            elapsed_ms=0,
        )
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def format_run_output(result: RunResult) -> str:
    """
    格式化 RunResult 为展示用的文本。

    包含：
    - 执行状态（成功/超时/错误）
    - 标准输出
    - 标准错误
    - 耗时统计
    """
    lines = []

    # 状态行
    if result.timed_out:
        lines.append("⏰ **执行超时** — 代码运行超过了时间限制。")
        lines.append("")
    elif result.exit_code == 0 and not result.stderr:
        lines.append("✅ **执行成功**")
        lines.append("")
    elif result.exit_code != 0:
        lines.append(f"❌ **执行失败** — 退出码: {result.exit_code}")
        lines.append("")
    else:
        lines.append("⚠️ **执行完成（有警告）**")
        lines.append("")

    # 标准输出
    if result.stdout.strip():
        lines.append("📤 **标准输出 (stdout):**")
        lines.append("─" * 50)
        lines.append(result.stdout.rstrip())
        lines.append("─" * 50)
        lines.append("")

    # 标准错误
    if result.stderr.strip():
        lines.append("📥 **标准错误 (stderr):**")
        lines.append("─" * 50)
        lines.append(result.stderr.rstrip())
        lines.append("─" * 50)
        lines.append("")

    # 耗时
    if result.elapsed_ms > 0:
        if result.elapsed_ms < 1000:
            lines.append(f"⏱ 耗时: {result.elapsed_ms:.0f} ms")
        else:
            lines.append(f"⏱ 耗时: {result.elapsed_ms / 1000:.2f} s")

    return "\n".join(lines)
