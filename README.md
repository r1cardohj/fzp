# fzp

A minimal [fzf](https://github.com/junegunn/fzf) clone written in Python. The first version (MVP) focuses on the **core algorithm** and a minimal usable interaction: feed it file paths or piped input, fuzzy search, press Enter to print the result.

![demo](https://img.shields.io/badge/python-3.12%2B-blue)

## Quick Start

```bash
git clone <repo> && cd fzp
uv sync

uv run fzp                  # scan the current directory, print the selected path to stdout
ls | uv run fzp             # read candidates from a pipe
vim $(ls | uv run fzp)      # use with command substitution
uv run fzp -q cli           # start with an initial query
```

Key bindings:

| Key | Action |
| --- | --- |
| `↑` / `Ctrl-P` | Move up |
| `↓` / `Ctrl-N` / `Ctrl-J` | Move down |
| `PgUp` / `PgDn` | Page up / down |
| `Enter` | Confirm, print the selected item to stdout |
| `Esc` / `Ctrl-C` / `Ctrl-D` / `Ctrl-G` | Cancel, exit code 130 |

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
└── tui.py     # prompt_toolkit interactive UI (query line / result list / status bar)
tests/         # pytest: algorithm, directory scan, CLI
scripts/pty_smoke.py  # smoke test driving a real interactive session via pty
```

## Development

```bash
uv run pytest                 # unit tests
uv run python scripts/pty_smoke.py   # interactive smoke test (requires a pty)
```

## Roadmap

- Multi-select (Tab to toggle, `--multi`)
- Result preview (`--preview`)
- Candidate caching / incremental reading for huge inputs
- DP (Smith-Waterman) scoring to get even closer to fzf v2
