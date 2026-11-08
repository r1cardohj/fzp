from __future__ import annotations

import re

import pytest
from prompt_toolkit.input.base import DummyInput
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.styles import Style

import fzp.tui as tui

from fzp.tui import (
    MAX_VISIBLE_RESULTS,
    NO_MATCH,
    PROMPT,
    STYLE,
    Picker,
    status_text,
)


@pytest.fixture(autouse=True)
def dummy_terminal(monkeypatch):
    """这些单元测试不需要真实终端，在 Windows CI 中也不能访问控制台。"""
    monkeypatch.setattr(tui, "create_input", lambda **kwargs: DummyInput())
    monkeypatch.setattr(tui, "create_output", lambda *args, **kwargs: DummyOutput())

CJK = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


def _rule(style: Style, class_name: str) -> str:
    for name, value in style.style_rules:
        if name == class_name:
            return value
    raise AssertionError(f"missing style rule: {class_name}")


def test_ui_texts_are_english():
    for text in (PROMPT, NO_MATCH, status_text(1, 3, 10), status_text(0, 0, 10)):
        assert not CJK.search(text), text


def test_status_text():
    assert status_text(1, 3, 10) == "  1/3  (10 items)"
    assert status_text(0, 0, 10) == "  0/10  (10 items)"


def test_picker_is_inline_and_erased_on_exit():
    """Ctrl-T 场景必须保留 shell 屏幕，在光标下方展开，而不是全屏清屏。"""
    picker = Picker(["a", "b"])
    assert picker.app is not None
    assert picker.app.full_screen is False
    assert picker.app.erase_when_done is True
    assert picker._visible_rows() == 2


def test_visible_results_are_capped():
    picker = Picker([str(i) for i in range(50)])
    assert picker._visible_rows() == MAX_VISIBLE_RESULTS


def test_match_is_foreground_highlight_not_background():
    """命中字符只换文字颜色，不使用背景色 / 反显。"""
    for class_name in ("match", "current match", "current", "pointer"):
        rule = _rule(STYLE, class_name)
        assert "reverse" not in rule, (class_name, rule)
        assert "bg:" not in rule and "bgcolor" not in rule, (class_name, rule)
        assert "fg:" in rule, (class_name, rule)


def test_match_uses_a_distinct_color_from_current_line():
    match_rule = _rule(STYLE, "match")
    current_rule = _rule(STYLE, "current")
    assert "ansibrightgreen" in match_rule
    assert "ansibrightgreen" not in current_rule
