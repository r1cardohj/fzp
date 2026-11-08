"""fzp 的核心：fuzzy 匹配 + 打分。

不依赖任何第三方 fuzzy 库，算法思路参考 fzf v1：

1. 子序列匹配（大小写不敏感）。
2. 取两种对齐方式里得分更高的那个：
   - 正向贪心：每个 pattern 字符取最早出现的位置（容易得到连续命中）；
   - 反向贪心：每个 pattern 字符取最晚出现的位置（容易贴近文件名）。
3. 按下面的规则打分：
   - 每命中一个字符                    +SCORE_MATCH
   - 命中在串首                        +BONUS_HEAD
   - 命中在分隔符 / 驼峰 / 数字字母边界  +BONUS_BOUNDARY
   - 与前一个命中相邻                   +BONUS_CONSECUTIVE
   - 大小写也一致                       +BONUS_CASE_MATCH
   - 中间跳过字符                       -PENALTY_GAP_START - n * PENALTY_GAP_EXTENSION

   连续命中 + 词首命中的组合得分最高，所以 "app" 会优先命中 `app.py`，
   而不是 `a_pp_p.py`。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

SCORE_MATCH = 16
BONUS_BOUNDARY = SCORE_MATCH // 2  # 分隔符/驼峰之后
BONUS_HEAD = 2 * BONUS_BOUNDARY  # 串首命中
BONUS_CONSECUTIVE = SCORE_MATCH  # 连续命中
BONUS_CASE_MATCH = 2  # 大小写一致
PENALTY_GAP_START = 3  # 第一次跳字符
PENALTY_GAP_EXTENSION = 1  # 之后每多跳一个字符

# 词边界分隔符
SEPARATORS = frozenset("/\\._-:;,| \t[](){}<>+=$#@!*?\"'`~&%")


@dataclass(frozen=True)
class Match:
    """一次成功匹配：总分 + 命中字符下标（用于高亮）。"""

    score: int
    positions: tuple[int, ...]


def _position_bonus(text: str, index: int) -> int:
    """命中 text[index] 的“位置加成”。"""
    if index == 0:
        return BONUS_HEAD
    prev, cur = text[index - 1], text[index]
    if prev in SEPARATORS:
        return BONUS_BOUNDARY
    if prev.islower() and cur.isupper():  # camelCase
        return BONUS_BOUNDARY
    if prev.isdigit() != cur.isdigit() and cur.isalnum():  # a1 / 1a
        return BONUS_BOUNDARY
    return 0


def _forward_positions(lowered: str, haystack: str) -> list[int] | None:
    """每个字符取最早出现的位置。"""
    positions: list[int] = []
    start = 0
    for char in lowered:
        found = haystack.find(char, start)
        if found < 0:
            return None
        positions.append(found)
        start = found + 1
    return positions


def _backward_positions(lowered: str, haystack: str) -> list[int] | None:
    """每个字符取最晚出现的位置（从右往左贪心）。"""
    positions = [0] * len(lowered)
    limit = len(haystack)
    for i in range(len(lowered) - 1, -1, -1):
        found = haystack.rfind(lowered[i], 0, limit)
        if found < 0:
            return None
        positions[i] = found
        limit = found
    return positions


def _score(text: str, pattern: str, positions: Sequence[int]) -> int:
    score = 0
    previous = -2
    for index, char in zip(positions, pattern):
        score += SCORE_MATCH
        if index == previous + 1:
            score += BONUS_CONSECUTIVE
        elif previous >= 0:
            gap = index - previous - 1
            score -= PENALTY_GAP_START + PENALTY_GAP_EXTENSION * (gap - 1)
        score += _position_bonus(text, index)
        if text[index] == char:
            score += BONUS_CASE_MATCH
        previous = index
    return score


def fuzzy_match(pattern: str, text: str) -> Match | None:
    """pattern 是 text 的子序列则返回 Match，否则 None。空 pattern 恒命中。"""
    if not pattern:
        return Match(0, ())

    lowered = pattern.lower()
    haystack = text.lower()
    if len(lowered) > len(haystack):
        return None

    candidates = [
        positions
        for positions in (
            _forward_positions(lowered, haystack),
            _backward_positions(lowered, haystack),
        )
        if positions is not None
    ]
    if not candidates:
        return None

    best = max(candidates, key=lambda positions: _score(text, pattern, positions))
    return Match(_score(text, pattern, best), tuple(best))


def fuzzy_filter(pattern: str, items: Sequence[str]) -> list[tuple[str, Match]]:
    """过滤 + 排序，返回 [(原始条目, Match), ...]。

    空 pattern 保持输入顺序（和 fzf 一样），非空 pattern 按分数降序，
    同分时更短、更靠前的条目优先。
    """
    if not pattern:
        return [(item, Match(0, ())) for item in items]

    scored: list[tuple[int, int, int, str, Match]] = []
    for order, item in enumerate(items):
        match = fuzzy_match(pattern, item)
        if match is not None:
            scored.append((-match.score, len(item), order, item, match))

    scored.sort()
    return [(item, match) for _, _, _, item, match in scored]
