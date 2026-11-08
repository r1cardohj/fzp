# fzp

用 Python 写的极简 [fzf](https://github.com/junegunn/fzf)。第一版（MVP）先把
**核心算法**和最小的可用交互做出来：输入文件路径/管道内容，fuzzy 搜索，回车输出。

![demo](https://img.shields.io/badge/python-3.12%2B-blue)

## 快速开始

```bash
git clone <repo> && cd fzp
uv sync

uv run fzp                  # 扫描当前目录，选中后把路径打印到 stdout
ls | uv run fzp             # 从管道读取候选
vim $(ls | uv run fzp)      # 配合命令替换使用
uv run fzp -q cli           # 带初始查询串启动
```

交互键位：

| 键位 | 作用 |
| --- | --- |
| `↑` / `Ctrl-P` | 上移 |
| `↓` / `Ctrl-N` / `Ctrl-J` | 下移 |
| `PgUp` / `PgDn` | 翻页 |
| `Enter` | 确认，把选中条目打印到 stdout |
| `Esc` / `Ctrl-C` / `Ctrl-D` / `Ctrl-G` | 取消，退出码 130 |

界面画在 stderr 上，stdout 只输出最终结果，所以可以直接用于管道和 `$( )`。
界面文案全英文（`❯ ` 提示符、`<no match>`、`1/3  (4 items)` 状态栏）；
fuzzy 命中的字符用**文字颜色**（亮绿 + 下划线）高亮，不使用背景色或反显，
选中的行用亮青加粗表示。

## 核心算法（`src/fzp/fuzzy.py`）

不依赖任何第三方 fuzzy 库，思路参考 fzf v1：

1. **子序列匹配**：pattern 的字符按顺序出现在候选中即命中，大小写不敏感。
2. **两种对齐取更优**：正向贪心（每个字符取最早出现位置，容易连续命中）与
   反向贪心（每个字符取最晚出现位置，容易贴近文件名末尾），两者取分数高者。
3. **打分规则**：

   | 规则 | 分值 |
   | --- | --- |
   | 每命中一个字符 | +16 |
   | 命中在串首 | +16 |
   | 命中在分隔符（`/ . _ - : ; , |` 空格等）或驼峰 / 数字字母边界之后 | +8 |
   | 与前一个命中相邻 | +16 |
   | 大小写也一致 | +2 |
   | 中间每跳过一段字符 | -3，之后每多跳 1 个字符再 -1 |

4. **排序**：分数降序，同分时更短、更靠前的条目优先；空查询保持输入顺序（和 fzf 一致）。

因此 `app` 会优先命中 `app.py`，而不是 `a_p_p.py`：

```python
>>> from fzp import fuzzy_filter
>>> [item for item, _ in fuzzy_filter("app", ["a_p_p.py", "src/app.py", "app.py"])]
['app.py', 'src/app.py', 'a_p_p.py']```

## 项目结构

```
src/fzp/
├── cli.py     # click 入口：管道检测、目录扫描、输出结果
├── fuzzy.py   # 核心 fuzzy 匹配 + 打分 + 排序（纯函数，好测）
├── files.py   # 无管道输入时扫描当前目录
└── tui.py     # prompt_toolkit 交互界面（查询行 / 结果列表 / 状态栏）
tests/         # pytest：算法、目录扫描、CLI
scripts/pty_smoke.py  # 用 pty 跑真实交互的冒烟测试
```

## 开发

```bash
uv run pytest                 # 单元测试
uv run python scripts/pty_smoke.py   # 交互冒烟测试（需要 pty）
```

## 后续计划

- 多选（Tab 标记，`--multi`）
- 结果预览（`--preview`）
- 候选来源缓存 / 增量读取超大输入
- DP（Smith-Waterman）版本打分，进一步贴近 fzf v2 的打分
