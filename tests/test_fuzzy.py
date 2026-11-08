from __future__ import annotations

import pytest

from fzp.fuzzy import fuzzy_filter, fuzzy_match


def test_empty_pattern_matches_everything():
    match = fuzzy_match("", "anything")
    assert match is not None
    assert match.score == 0
    assert match.positions == ()


def test_not_a_subsequence():
    assert fuzzy_match("abc", "acb") is None
    assert fuzzy_match("toolong", "tiny") is None


def test_case_insensitive_subsequence():
    match = fuzzy_match("APP", "src/app.py")
    assert match is not None
    assert match.positions == (4, 5, 6)


def test_contiguous_match_beats_scattered_one():
    items = ["a_p_p.py", "app.py", "x_app.py"]
    ranked = [item for item, _ in fuzzy_filter("app", items)]
    # 连续命中 + 词首命中，`app.py` 应该排在 `a_p_p.py` 前面
    assert ranked.index("app.py") < ranked.index("a_p_p.py")


def test_contiguous_match_beats_boundary_separated():
    items = ["a_p_p.py", "src/app.py", "app.py"]
    assert [item for item, _ in fuzzy_filter("app", items)] == [
        "app.py",
        "src/app.py",
        "a_p_p.py",
    ]


def test_word_boundary_is_preferred():
    assert fuzzy_match("fb", "foo/bar") is not None
    boundary = fuzzy_match("fb", "foo/bar")
    scattered = fuzzy_match("fb", "xfxxb")
    assert boundary.score > scattered.score


def test_prefix_bonus():
    head = fuzzy_match("ab", "abc")
    later = fuzzy_match("ab", "zab")
    assert head.score > later.score


def test_gap_penalty():
    tight = fuzzy_match("ab", "axb")
    loose = fuzzy_match("ab", "axxxxxxxxxxb")
    assert tight.score > loose.score


def test_case_match_bonus():
    exact = fuzzy_match("app", "app.py")
    folded = fuzzy_match("APP", "app.py")
    assert exact.score > folded.score


def test_positions_are_valid_and_sorted():
    match = fuzzy_match("py", "src/fzp/cli.py")
    assert match is not None
    text = "src/fzp/cli.py"
    assert list(match.positions) == sorted(match.positions)
    assert [text[i] for i in match.positions] == ["p", "y"]


def test_filter_keeps_input_order_for_empty_query():
    items = ["b", "a", "c"]
    assert [item for item, _ in fuzzy_filter("", items)] == items


def test_filter_drops_non_matching_items():
    ranked = fuzzy_filter("cli", ["src/fzp/cli.py", "README.md", "client.py"])
    assert sorted(item for item, _ in ranked) == ["client.py", "src/fzp/cli.py"]


@pytest.mark.parametrize("pattern", ["fzp", "cl", "py", "srccli"])
def test_filter_is_sorted_by_descending_score(pattern):
    items = [".gitignore", "README.md", "pyproject.toml", "src/fzp/cli.py", "src/fzp/tui.py"]
    scores = [match.score for _, match in fuzzy_filter(pattern, items)]
    assert scores == sorted(scores, reverse=True)
