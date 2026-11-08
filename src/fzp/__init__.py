"""fzp —— 用 Python 写的极简 fzf。

核心是自研的 fuzzy 匹配打分算法，见 :mod:`fzp.fuzzy`。
"""

from .fuzzy import Match, fuzzy_filter, fuzzy_match

__all__ = ["Match", "fuzzy_filter", "fuzzy_match"]
__version__ = "0.1.0"
