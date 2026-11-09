"""fzp 命令行入口。"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .files import read_candidates, walk_files
from .fuzzy import fuzzy_filter


def _has_tty() -> bool:
    streams = (sys.stdin, sys.stdout, sys.stderr)
    return any(stream is not None and stream.isatty() for stream in streams)


@click.group(
    invoke_without_command=True,
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(package_name="fzp", prog_name="fzp")
@click.option("-q", "--query", default="", help="Initial query string.")
@click.option(
    "--hidden/--no-hidden",
    default=False,
    show_default=True,
    help="Include hidden files when scanning the current directory.",
)
@click.pass_context
def main(ctx: click.Context, query: str, hidden: bool) -> None:
    """fzp - a tiny fzf in Python: fuzzy-search files or piped input.

    \b
    Examples:
      fzp                    # scan the current directory, print the selection
      ls | fzp               # read candidates from a pipe
      vim $(ls | fzp)        # hand the selection to another command
      fzp setup              # install Ctrl-T / Ctrl-R bindings into ~/.bashrc
    """
    if ctx.invoked_subcommand is not None:
        return
    _run_picker(query, hidden)


def _run_picker(query: str, hidden: bool) -> None:
    items: list[str] = []
    if sys.stdin is not None and not sys.stdin.isatty():
        items = list(read_candidates(sys.stdin))
    else:
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


@main.command()
@click.option(
    "--show",
    "show_only",
    is_flag=True,
    help="Print the snippet that would be written, don't touch any file.",
)
@click.option(
    "--rc",
    "rc_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Write to this rc file instead of the one detected from $SHELL.",
)
@click.pass_context
def setup(ctx: click.Context, show_only: bool, rc_path: Path | None) -> None:
    """Install Ctrl-T file completion and Ctrl-R history search.

    Writes a key-binding block (idempotent, wrapped in marker comments) into your
    shell rc file. bash gets live bindings; other shells keep the block inert until
    their integration lands.
    """
    from . import setup as setup_mod

    try:
        rc = rc_path or setup_mod.detect_shell_rc()
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    if show_only:
        old = rc.read_text(encoding="utf-8") if rc.exists() else ""
        click.echo(setup_mod.render_preview(old), nl=False)
        return

    try:
        setup_mod.setup_key_bindings(rc)
    except OSError as exc:
        raise click.ClickException(f"Failed to write {rc}: {exc}") from exc

    click.secho(f"✔ Shell integration written to {rc}", fg="green")
    click.secho(
        "  Restart your shell, or run:  "
        + click.style(f"source {rc}", fg="cyan", bold=True),
    )
    click.secho(
        "  Then press Ctrl-T to fuzzy-pick a file or Ctrl-R to search history.",
        dim=True,
    )


if __name__ == "__main__":  # python -m fzp.cli
    main()
