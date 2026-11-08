"""PTY 冒烟测试：用真实终端跑一遍交互界面 + 管道输入。"""

import os
import pty
import re
import select
import subprocess
import sys
import time

ANSI = re.compile(
    rb"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[()][A-B0-9]|\x1b[=>]"
)

def _drain(master, timeout):
    chunk = b""
    while True:
        ready, _, _ = select.select([master], [], [], timeout)
        if not ready:
            return chunk
        try:
            data = os.read(master, 65536)
        except OSError:
            return chunk
        if not data:
            return chunk
        chunk += data
        timeout = 0


def run(args, keys, stdin_data=None, timeout=20.0):
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE if stdin_data is not None else slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)
    if stdin_data is not None:
        proc.stdin.write(stdin_data.encode())
        proc.stdin.close()

    time.sleep(0.8)  # 等 prompt_toolkit 起来并进入 raw 模式
    out = _drain(master, 0.2)
    for key in keys:
        os.write(master, key)
        out += _drain(master, 0.3)

    deadline = time.time() + timeout
    while time.time() < deadline and proc.poll() is None:
        out += _drain(master, 0.2)
    proc.wait(timeout=5)
    os.close(master)
    return proc.returncode, ANSI.sub(b"", out).decode(errors="replace"), out


def _lines(out):
    return [line for line in out.replace("\r", "").splitlines() if line.strip()]


def main():
    # 1) 管道输入 + 交互过滤 + 回车
    code, out, raw = run(
        [sys.executable, "-m", "fzp.cli"],
        [b"c", b"l", b"i", b"\r"],
        stdin_data="src/fzp/cli.py\nREADME.md\npyproject.toml\n",
    )
    print("case1 exit:", code, "| selected path printed:", "src/fzp/cli.py" in out)
    assert code == 0, code
    assert "src/fzp/cli.py" in out, out
    # 内联模式：不能切换到 alternate screen（会清屏 / 从终端顶部开始）。
    assert b"\x1b[?1049h" not in raw, raw[:1000]
    # 样式检查：不能用背景色 / 反显，命中字符用前景色（亮绿 92）
    sgr = set(re.findall(rb"\x1b\[([0-9;]*)m", raw))
    assert not any(b"7" in params.split(b";") for params in sgr), sgr
    assert not any(b"48" in params.split(b";") for params in sgr), sgr
    assert any(b"92" in params.split(b";") for params in sgr), sgr
    assert "<no match>" not in out

    # 2) 无管道：扫描当前目录，-q 预填查询，直接回车
    code, out, raw = run([sys.executable, "-m", "fzp.cli", "-q", "tui"], [b"\r"])
    print("case2 exit:", code, "| selected path printed:", "src/fzp/tui.py" in out)
    assert code == 0, code
    assert "src/fzp/tui.py" in out, out

    # 3) Esc 取消 -> 退出码 130，且不输出结果
    code, out, _ = run([sys.executable, "-m", "fzp.cli"], [b"\x1b"], stdin_data="a\nb\n")
    print("case3 exit:", code)
    assert code == 130, code

    # 4) 上下键移动选择
    code, out, _ = run(
        [sys.executable, "-m", "fzp.cli"],
        [b"\x1b[B", b"\x1b[B", b"\r"],
        stdin_data="".join(f"file{i}.py\n" for i in range(5)),
    )
    print("case4 exit:", code, "| selected path printed:", "file2.py" in out)
    assert code == 0, code
    assert "file2.py" in out, out

    # 5) 无匹配时的英文提示（输入三个 z 后再 Esc 退出）
    code, out, _ = run(
        [sys.executable, "-m", "fzp.cli"],
        [b"z", b"z", b"z", b"\x1b"],
        stdin_data="a\nb\n",
    )
    print("case5 exit:", code, "| has no-match hint:", "<no match>" in out)
    assert code == 130, code
    assert "<no match>" in out, out[-500:]
    assert "(2 items)" in out, out[-500:]

    print("OK")


if __name__ == "__main__":
    main()
