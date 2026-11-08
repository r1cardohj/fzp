from __future__ import annotations

from click.testing import CliRunner

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
