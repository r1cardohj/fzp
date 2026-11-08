"""fzp 命令行入口。"""

from __future__ import annotations

import sys

import click

from .files import read_candidates, walk_files
from .fuzzy import fuzzy_filter


def _has_tty() -> bool:
    streams = (sys.stdin, sys.stdout, sys.stderr)
    return any(stream is not None and stream.isatty() for stream in streams)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="fzp", prog_name="fzp")
@click.option("-q", "--query", default="", help="Initial query string.")
@click.option(
    "--hidden/--no-hidden",
    default=False,
    show_default=True,
    help="Include hidden files when scanning the current directory.",
)
def main(query: str, hidden: bool) -> None:
    """fzp - a tiny fzf in Python: fuzzy-search files or piped input.

    \b
    Examples:
      fzp                    # scan the current directory, print the selection
      ls | fzp               # read candidates from a pipe
      vim $(ls | fzp)        # hand the selection to another command
    """
    items: list[str] = []
    if sys.stdin is not None and not sys.stdin.isatty():
        items = list(read_candidates(sys.stdin))

    if not items:
        items = walk_files(".", hidden=hidden)

    items = [item for item in items if item.strip()]
    if not items:
        raise click.ClickException("No candidates found")

    # 没有终端（比如在脚本里跑）时退化成纯过滤，方便测试和自动化
    if not _has_tty():
        for item, _ in fuzzy_filter(query, items):
            click.echo(item)
        return

    from .tui import Picker  # 延迟导入：非交互模式不需要 prompt_toolkit

    selected = Picker(items, query=query).pick()
    if selected is None:
        raise SystemExit(130)
    click.echo(selected)


if __name__ == "__main__":  # python -m fzp.cli
    main()
