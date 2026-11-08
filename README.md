# fzp

A minimal [fzf](https://github.com/junegunn/fzf) clone written in Python. The first version (MVP) focuses on the **core algorithm** and a minimal usable interaction: feed it file paths or piped input, fuzzy search, press Enter to print the result.

![CI](https://github.com/r1cardohj/fzp/actions/workflows/ci.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/fzp)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)

## Installation

```bash
pip install fzp
# Or install an isolated CLI with uv:
uv tool install fzp
```

## Quick Start

```bash
fzp                         # scan the current directory, print the selected path
ls | fzp                    # read candidates from a pipe
vim $(ls | fzp)             # use with command substitution
fzp -q cli                  # start with an initial query
fzp setup                   # install the Ctrl-T key-binding into ~/.bashrc
```

### From source

```bash
git clone https://github.com/r1cardohj/fzp.git && cd fzp
uv sync

uv run fzp                  # scan the current directory, print the selected path to stdout
ls | uv run fzp             # read candidates from a pipe
vim $(ls | uv run fzp)      # use with command substitution
uv run fzp -q cli           # start with an initial query
uv run fzp setup            # install the Ctrl-T key-binding into ~/.bashrc
```

## Shell Integration (`fzp setup`)

Just like `fzf`'s key bindings, `fzp setup` writes a small block into your shell rc file
(the file is chosen from `$SHELL`: `.bashrc` for bash, `.zshrc` for zsh) and prints a
reminder to re-source it:

```bash
fzp setup          # write to ~/.bashrc (or ~/.zshrc) and hint: source ~/.bashrc
fzp setup --show   # print the snippet that would be written, don't touch any file
```

After restarting your shell (or `source ~/.bashrc`), press **Ctrl-T** on the command line
to open fzp: the selected path is pasted at the cursor, followed by a space, ready for the
next argument. Ending the line with `^` appends the selection instead of replacing
(`cat notes.md ^` + Ctrl-T → `cat notes.md src/fzp/cli.py`).

The block is wrapped in `# >>> fzp key-bindings >>>` / `# <<< fzp key-bindings <<<`
markers, so re-running `fzp setup` is idempotent (it replaces the old block in place),
and deleting the block uninstalls the binding.

> Only bash gets a live binding for now (`bind -x '\C-t'` via readline); on zsh the block
> is written but inert until zsh integration lands.

Key bindings:

| Key | Action |
| --- | --- |
| `↑` / `Ctrl-P` | Move up |
| `↓` / `Ctrl-N` / `Ctrl-J` | Move down |
| `PgUp` / `PgDn` | Page up / down |
| `Enter` | Confirm, print the selected item to stdout |
| `Esc` / `Ctrl-C` / `Ctrl-D` / `Ctrl-G` | Cancel, exit code 130 |

The UI is drawn inline below the current cursor, with up to 10 visible candidates. It does
not clear the terminal or enter the alternate screen, and the picker is erased when done.
The UI is drawn on stderr, and stdout only carries the final result, so it works seamlessly with pipes and `$( )`.
All UI text is in English (`❯ ` prompt, `<no match>`, `1/3  (4 items)` status bar).
Matched characters are highlighted with a **text color** (bright green + underline) — no background color or reverse video;
the selected line is shown in bright cyan and bold.

## Core Algorithm (`src/fzp/fuzzy.py`)

No third-party fuzzy library is used. The approach is inspired by fzf v1:

1. **Subsequence matching**: a candidate matches if the pattern's characters appear in order; case-insensitive.
2. **Two alignments, pick the better one**: forward greedy (each character takes its earliest occurrence, favoring consecutive matches) and backward greedy (each character takes its latest occurrence, favoring matches near the end of the filename); the higher-scoring one wins.
3. **Scoring rules**:

   | Rule | Score |
   | --- | --- |
   | Each matched character | +16 |
   | Match at the start of the string | +16 |
   | Match right after a delimiter (`/ . _ - : ; , |`, space, etc.) or a camelCase / letter-digit boundary | +8 |
   | Adjacent to the previous match | +16 |
   | Exact case match | +2 |
   | Each skipped gap between matches | -3, then -1 for each additional skipped character |

4. **Sorting**: by score descending; ties prefer shorter items and earlier input order; an empty query preserves the input order (same as fzf).

So `app` ranks `app.py` above `a_p_p.py`:

```python
>>> from fzp import fuzzy_filter
>>> [item for item, _ in fuzzy_filter("app", ["a_p_p.py", "src/app.py", "app.py"])]
['app.py', 'src/app.py', 'a_p_p.py']
```

## Project Structure

```
src/fzp/
├── cli.py     # click entrypoint: pipe detection, directory scan, result output
├── fuzzy.py   # core fuzzy matching + scoring + sorting (pure functions, easy to test)
├── files.py   # scans the current directory when there's no piped input
├── setup.py   # shell integration and idempotent rc-file installation
└── tui.py     # prompt_toolkit interactive UI (query line / result list / status bar)
tests/         # pytest: algorithm, directory scan, CLI
scripts/pty_smoke.py  # smoke test driving a real interactive session via pty
```

## Development

```bash
uv run pytest                 # unit tests
uv run python scripts/pty_smoke.py   # interactive smoke test (requires a pty)
uv build                         # build the sdist and wheel
```

## Release

Releases use [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/),
so no long-lived API token is stored in GitHub. After registering the pending
publisher described in [RELEASING.md](RELEASING.md), push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The release workflow runs the test matrix, validates the built packages, and
publishes them to PyPI.

## Roadmap

- zsh integration (`bindkey` widget) to match the bash Ctrl-T binding
- Multi-select (Tab to toggle, `--multi`)
- Result preview (`--preview`)
- Candidate caching / incremental reading for huge inputs
- DP (Smith-Waterman) scoring to get even closer to fzf v2
