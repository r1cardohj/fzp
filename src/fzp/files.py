"""没有管道输入时，扫描当前目录下的文件，给 fzf 式的体验。"""

from __future__ import annotations

import os
from typing import Iterator

# 明显没有意义的目录，直接跳过
SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".idea",
        ".gradle",
        "target",
        "dist",
        "build",
    }
)

MAX_FILES = 200_000


def walk_files(root: str = ".", hidden: bool = False) -> list[str]:
    """返回 root 下所有文件的相对路径，顺序稳定（目录/文件名排序）。"""
    results: list[str] = []
    root = os.path.abspath(root)

    for current, dirs, files in os.walk(root):
        if not hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            # 统一用 POSIX 分隔符，Windows 下也输出 src/app.py。
            path = os.path.relpath(os.path.join(current, name), root)
            results.append(path.replace(os.sep, "/"))
            if len(results) >= MAX_FILES:
                return results

    return results


def read_candidates(stream) -> Iterator[str]:
    """把 stdin 的每一行当成一个候选项。"""
    for line in stream:
        yield line.rstrip("\n")
