"""fzp —— 用 Python 写的极简 fzf。

核心是自研的 fuzzy 匹配打分算法，见 :mod:`fzp.fuzzy`。
"""

from .files import walk_files
from .fuzzy import Match, fuzzy_filter, fuzzy_match

try:  # prompt_toolkit 缺失时退化成纯 fuzzy 库（无 TUI）
    from .tui import Picker
except ImportError:  # pragma: no cover
    Picker = None  # type: ignore[assignment]

__all__ = ["Match", "Picker", "fuzzy_filter", "fuzzy_match", "walk_files"]
__version__ = "0.2.2"
