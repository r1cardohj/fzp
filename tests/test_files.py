from __future__ import annotations

from fzp.files import walk_files


def test_walk_files_skips_noise(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("")
    (tmp_path / "README.md").write_text("")

    found = walk_files(str(tmp_path))
    assert found == ["README.md", "src/app.py"]


def test_walk_files_hidden_flag(tmp_path):
    (tmp_path / ".hidden").write_text("")
    (tmp_path / "visible").write_text("")

    assert walk_files(str(tmp_path)) == ["visible"]
    assert walk_files(str(tmp_path), hidden=True) == [".hidden", "visible"]
