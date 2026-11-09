from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from fzp import setup as setup_mod
from fzp.cli import main
from click.testing import CliRunner


def test_inject_appends_snippet(tmp_path: Path):
    rc = tmp_path / ".bashrc"
    rc.write_text("# existing config\nexport EDITOR=vim\n", encoding="utf-8")
    setup_mod.setup_key_bindings(rc)
    content = rc.read_text(encoding="utf-8")
    assert setup_mod.HEADER in content
    assert setup_mod.FOOTER in content
    assert "bind -x" in content
    assert "__fzp_select" in content
    assert "__fzp_history" in content
    assert "\\C-r" in content
    # 原有内容保留
    assert "export EDITOR=vim" in content


def test_inject_is_idempotent(tmp_path: Path):
    rc = tmp_path / ".bashrc"
    rc.write_text("", encoding="utf-8")
    setup_mod.setup_key_bindings(rc)
    first = rc.read_text(encoding="utf-8")
    setup_mod.setup_key_bindings(rc)
    second = rc.read_text(encoding="utf-8")
    assert first == second
    assert second.count(setup_mod.HEADER) == 1


def test_inject_replaces_existing_block(tmp_path: Path):
    rc = tmp_path / ".bashrc"
    rc.write_text("before\n" + setup_mod.build_shell_snippet("command fzp") + "\nafter\n", encoding="utf-8")
    setup_mod.setup_key_bindings(rc)
    content = rc.read_text(encoding="utf-8")
    assert content.count(setup_mod.HEADER) == 1
    assert content.index("before") < content.index(setup_mod.HEADER)
    assert content.index(setup_mod.FOOTER) < content.index("after")


def test_snippet_is_valid_bash_syntax():
    if shutil.which("bash") is None or sys.platform == "win32":
        pytest.skip("requires a Unix bash; Windows runners may expose a WSL launcher")
    import subprocess

    proc = subprocess.run(
        ["bash", "-n"],
        input=setup_mod.build_shell_snippet(),
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_bash_binding_pastes_selection_into_readline(tmp_path: Path):
    """在伪终端之外模拟 readline 环境，验证选中的路径会被填回 READLINE_LINE。"""
    if shutil.which("bash") is None or sys.platform == "win32":
        pytest.skip("requires a Unix bash; Windows runners may expose a WSL launcher")
    import subprocess

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_fzp = bin_dir / "fzp"
    fake_fzp.write_text("#!/bin/sh\nprintf 'src/fzp/cli.py'\n", encoding="utf-8")
    fake_fzp.chmod(0o755)
    snippet_file = tmp_path / "fzp-snippet.sh"
    snippet_file.write_text(
        setup_mod.build_shell_snippet(str(fake_fzp)), encoding="utf-8"
    )
    script = f"""
source {snippet_file}
READLINE_LINE='vim '
READLINE_POINT=${{#READLINE_LINE}}
__fzp_select
printf '%s|%s\\n' "$READLINE_LINE" "$READLINE_POINT"
"""
    # 故意不把 fake fzp 所在目录放进 PATH：绑定应使用记录的绝对路径。
    env = {"PATH": "/usr/bin:/bin"}
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    line, point = proc.stdout.strip().rsplit("|", 1)
    assert line == "vim src/fzp/cli.py "
    assert int(point) == len("vim src/fzp/cli.py ")

    # 追加模式：行尾有 ^ 时不覆盖已有内容
    script_append = script.replace("READLINE_LINE='vim '", "READLINE_LINE='cat notes.md ^'")
    proc = subprocess.run(["bash", "-c", script_append], capture_output=True, text=True, env=env)
    line, _ = proc.stdout.strip().rsplit("|", 1)
    assert line == "cat notes.md  src/fzp/cli.py"


def test_bash_history_binding_searches_recent_unique_commands(tmp_path: Path):
    """Ctrl-R 使用当前行作 query，以最新优先、去重后的历史替换命令行。"""
    if shutil.which("bash") is None or sys.platform == "win32":
        pytest.skip("requires a Unix bash; Windows runners may expose a WSL launcher")
    import subprocess

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_fzp = bin_dir / "fzp"
    fake_fzp.write_text(
        "#!/bin/sh\n"
        "cat > \"$FZP_TEST_INPUT\"\n"
        "printf '%s\\n' \"$@\" > \"$FZP_TEST_ARGS\"\n"
        "printf 'echo recent\\n'\n",
        encoding="utf-8",
    )
    fake_fzp.chmod(0o755)
    snippet_file = tmp_path / "fzp-snippet.sh"
    snippet_file.write_text(
        setup_mod.build_shell_snippet(str(fake_fzp)), encoding="utf-8"
    )
    history_file = tmp_path / "history-input"
    args_file = tmp_path / "args"
    script = f"""
history -c
history -s 'echo old'
history -s 'echo recent'
history -s 'echo old'
source {snippet_file}
READLINE_LINE='rec'
READLINE_POINT=1
__fzp_history
printf '%s|%s\\n' "$READLINE_LINE" "$READLINE_POINT"
"""
    env = {
        "PATH": "/usr/bin:/bin",
        "FZP_TEST_INPUT": str(history_file),
        "FZP_TEST_ARGS": str(args_file),
    }
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    line, point = proc.stdout.strip().rsplit("|", 1)
    assert line == "echo recent"
    assert int(point) == len("echo recent")
    assert history_file.read_text(encoding="utf-8") == "echo old\necho recent\n"
    assert args_file.read_text(encoding="utf-8") == "-q\nrec\n"


def test_bash_history_binding_cancel_preserves_readline(tmp_path: Path):
    if shutil.which("bash") is None or sys.platform == "win32":
        pytest.skip("requires a Unix bash; Windows runners may expose a WSL launcher")
    import subprocess

    fake_fzp = tmp_path / "fzp"
    fake_fzp.write_text("#!/bin/sh\ncat >/dev/null\nexit 130\n", encoding="utf-8")
    fake_fzp.chmod(0o755)
    snippet_file = tmp_path / "fzp-snippet.sh"
    snippet_file.write_text(
        setup_mod.build_shell_snippet(str(fake_fzp)), encoding="utf-8"
    )
    script = f"""
source {snippet_file}
READLINE_LINE='git status'
READLINE_POINT=4
__fzp_history
printf '%s|%s\\n' "$READLINE_LINE" "$READLINE_POINT"
"""
    proc = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "git status|4"


def test_detect_shell_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SHELL", "/usr/bin/bash")
    assert setup_mod.detect_shell_rc(tmp_path) == tmp_path / ".bashrc"
    monkeypatch.setenv("SHELL", "/bin/zsh")
    assert setup_mod.detect_shell_rc(tmp_path) == tmp_path / ".zshrc"
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    with pytest.raises(RuntimeError):
        setup_mod.detect_shell_rc(tmp_path)


def test_cli_setup_writes_and_hints(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["setup", "--rc", str(tmp_path / ".bashrc")])
    assert result.exit_code == 0, result.output
    assert "written to" in result.output
    assert "source" in result.output
    assert (tmp_path / ".bashrc").exists()
    # 幂等
    result2 = runner.invoke(main, ["setup", "--rc", str(tmp_path / ".bashrc")])
    assert result2.exit_code == 0
    assert (tmp_path / ".bashrc").read_text(encoding="utf-8").count(setup_mod.HEADER) == 1


def test_cli_setup_show_does_not_write(tmp_path: Path):
    rc = tmp_path / ".bashrc"
    runner = CliRunner()
    result = runner.invoke(main, ["setup", "--show", "--rc", str(rc)])
    assert result.exit_code == 0, result.output
    assert setup_mod.HEADER in result.output
    assert "2>/dev/null" not in result.output
    assert not rc.exists()
