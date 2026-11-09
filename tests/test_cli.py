from __future__ import annotations

from click.testing import CliRunner

from fzp import cli
from fzp.cli import main


def test_filters_piped_input():
    runner = CliRunner()
    result = runner.invoke(
        main, ["-q", "cli"], input="src/fzp/cli.py\nREADME.md\npyproject.toml\n"
    )
    assert result.exit_code == 0, result.output
    assert result.output == "src/fzp/cli.py\n"


def test_initial_query_can_be_empty():
    runner = CliRunner()
    result = runner.invoke(main, [], input="b\na\n")
    assert result.exit_code == 0, result.output
    # 空查询保持输入顺序
    assert result.output == "b\na\n"


def test_empty_pipe_does_not_fall_back_to_files(monkeypatch):
    """空的 history 管道应显示无候选，而不是意外打开文件选择器。"""
    monkeypatch.setattr(cli, "walk_files", lambda *args, **kwargs: ["unexpected.py"])
    runner = CliRunner()
    result = runner.invoke(main, [], input="")
    assert result.exit_code == 1
    assert "No candidates found" in result.output
    assert "unexpected.py" not in result.output
