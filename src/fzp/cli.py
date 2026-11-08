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
@click.option("-q", "--query", default="", help="启动时的初始查询串。")
@click.option(
    "--hidden/--no-hidden",
    default=False,
    show_default=True,
    help="扫描当前目录时是否包含隐藏文件。",
)
def main(query: str, hidden: bool) -> None:
    """fzp —— Python 写的极简 fzf：fuzzy 搜索文件或管道输入。

    \b
    用法示例：
      fzp                    # 扫描当前目录，选中后打印路径
      ls | fzp               # 从管道读取候选
      vim $(ls | fzp)        # 把选中的文件交给别的命令
    """
    items: list[str] = []
    if sys.stdin is not None and not sys.stdin.isatty():
        items = list(read_candidates(sys.stdin))

    if not items:
        items = walk_files(".", hidden=hidden)

    items = [item for item in items if item.strip()]
    if not items:
        raise click.ClickException("没有找到任何候选条目")

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
