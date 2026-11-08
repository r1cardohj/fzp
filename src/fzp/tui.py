"""极简 fzf 式交互界面（prompt_toolkit）。界面文案统一用英文。"""

from __future__ import annotations

import asyncio
import sys
from typing import IO, Sequence

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.output import Output, create_output
from prompt_toolkit.styles import Style

from .fuzzy import Match, fuzzy_filter

STYLE = Style.from_dict(
    {
        "prompt": "fg:#5f87d7 bold",
        "pointer": "fg:ansibrightcyan bold",
        # 选中的行：换颜色 + 加粗（不用背景色）
        "current": "fg:ansibrightcyan bold",
        # fuzzy 命中的字符：纯文字高亮（换前景色 + 加粗，不用背景色）
        "match": "fg:ansibrightgreen bold",
        "current match": "fg:ansibrightgreen bold underline",
        "empty": "fg:#808080",
        "info": "fg:#808080",
    }
)

# 界面文案集中在这里，保持全英文
PROMPT = "❯ "
NO_MATCH = "<no match>"
MAX_VISIBLE_RESULTS = 10


def status_text(position: int, matches: int, total: int) -> str:
    """状态栏：当前第几个/匹配数/总数。"""
    if matches == 0:
        return f"  0/{total}  ({total} items)"
    return f"  {position}/{matches}  ({total} items)"


class Picker:
    """在候选列表里 fuzzy 搜索、上下选择、回车确认。

    pick() 返回选中的条目；用户按 Ctrl-C / Esc 时返回 None。
    需要嵌到别的 prompt_toolkit 应用里时用 pick_async(host=app)。
    """

    def __init__(
        self,
        items: Sequence[str],
        query: str = "",
        input: object | None = None,  # PosixPipeInput / create_pipe_input()
        output: IO[str] | Output | None = None,
    ) -> None:
        """``input``/``output`` override the TTY streams (for embedding).

        Pass a pipe input and a text stream (or an existing ``Output``) to
        render inline inside another prompt_toolkit application instead of
        taking over the terminal.
        """
        self.items = list(items)
        self.results: list[tuple[str, Match]] = []
        self.pointer = 0
        self.offset = 0
        self.app: Application[str] | None = None
        # 嵌入模式下的宿主应用（见 pick_async）。
        self._host: Application | None = None

        self.query_buffer = Buffer(multiline=False)
        self.query_buffer.text = query
        self.query_buffer.on_text_changed += self._on_query_changed

        prompt = Window(
            FormattedTextControl([("class:prompt", PROMPT)]),
            width=len(PROMPT),
            height=1,
        )
        query_line = VSplit(
            [prompt, Window(BufferControl(buffer=self.query_buffer), height=1)]
        )
        self.results_window = Window(
            FormattedTextControl(self._render_results),
            wrap_lines=False,
        )
        status = Window(
            FormattedTextControl(self._render_status), height=1, style="class:info"
        )

        layout = Layout(HSplit([query_line, self.results_window, status]))
        resolved_output: Output
        if output is None:
            resolved_output = create_output(self._ui_stream())
        elif isinstance(output, Output):
            resolved_output = output
        else:
            resolved_output = create_output(output)
        self.app = Application(
            layout=layout,
            key_bindings=self._key_bindings(),
            full_screen=False,
            erase_when_done=True,
            mouse_support=False,
            style=STYLE,
            input=input if input is not None else create_input(always_prefer_tty=True),
            output=resolved_output,
        )
        self._refresh()

    # ------------------------------------------------------------------ 状态

    def _ui_stream(self):
        """界面画到 stderr，stdout 只留给最终结果（方便管道/命令替换）。"""
        if sys.stderr is not None and sys.stderr.isatty():
            return sys.stderr
        return sys.stdout

    def _visible_rows(self) -> int:
        """候选区高度：最多 10 行，少候选时不撑出多余空白。"""
        if not self.results:
            return 1
        try:
            rows = get_app().output.get_size().rows
        except Exception:
            rows = 24
        return max(1, min(len(self.results), MAX_VISIBLE_RESULTS, rows - 2))

    def _on_query_changed(self, _buffer: Buffer) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.results = fuzzy_filter(self.query_buffer.text, self.items)
        self.pointer = 0
        self.offset = 0
        self._invalidate()

    def _invalidate(self) -> None:
        """嵌入时重绘宿主应用，独立运行时重绘自己的应用。"""
        target = self._host if self._host is not None else self.app
        if target is not None:
            target.invalidate()

    def _current(self) -> str | None:
        if not self.results:
            return None
        return self.results[self.pointer][0]

    def _move(self, delta: int) -> None:
        if not self.results:
            return
        self.pointer = min(max(self.pointer + delta, 0), len(self.results) - 1)
        visible = self._visible_rows()
        if self.pointer < self.offset:
            self.offset = self.pointer
        elif self.pointer >= self.offset + visible:
            self.offset = self.pointer - visible + 1

    # ------------------------------------------------------------------ 渲染

    @staticmethod
    def _fragments(text: str, positions: tuple[int, ...], selected: bool):
        """把一行拆成普通字符 / 命中字符（用于高亮）。"""
        plain = "class:current" if selected else ""
        hit = "class:current class:match" if selected else "class:match"
        fragments = []
        last = 0
        for position in positions:
            if position > last:
                fragments.append((plain, text[last:position]))
            fragments.append((hit, text[position]))
            last = position + 1
        if last < len(text):
            fragments.append((plain, text[last:]))
        return fragments

    def _render_results(self):
        visible = self._visible_rows()

        if not self.results:
            return [("class:empty", f"  {NO_MATCH}")]

        self.offset = max(0, min(self.offset, len(self.results) - 1))
        if self.pointer < self.offset:
            self.offset = self.pointer
        elif self.pointer >= self.offset + visible:
            self.offset = self.pointer - visible + 1

        lines = []
        end = min(self.offset + visible, len(self.results))
        for index in range(self.offset, end):
            text, match = self.results[index]
            selected = index == self.pointer
            marker = "> " if selected else "  "
            lines.append(
                (
                    "class:current class:pointer" if selected else "class:pointer",
                    marker,
                )
            )
            lines.extend(self._fragments(text, match.positions, selected))
            if index != end - 1:
                lines.append(("", "\n"))
        return lines

    def _render_status(self):
        return status_text(self.pointer + 1, len(self.results), len(self.items))

    # -------------------------------------------------------------- 键位绑定

    def _key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("down")
        @bindings.add("c-n")
        @bindings.add("c-j")
        def _down(event) -> None:
            self._move(1)

        @bindings.add("up")
        @bindings.add("c-p")
        def _up(event) -> None:
            self._move(-1)

        @bindings.add("pageup")
        def _page_up(event) -> None:
            self._move(-self._visible_rows())

        @bindings.add("pagedown")
        def _page_down(event) -> None:
            self._move(self._visible_rows())

        @bindings.add("enter")
        def _accept(event) -> None:
            self._exit(self._current())

        @bindings.add("c-c")
        @bindings.add("c-d")
        @bindings.add("c-g")
        @bindings.add("escape")
        def _abort(event) -> None:
            self._exit(None)

        return bindings

    def _exit(self, result: str | None) -> None:
        """幂等退出：快速连按退出键时避免重复调用 Application.exit() 抛异常。"""
        assert self.app is not None
        if self.app.future is not None and not self.app.future.done():
            self.app.exit(result=result)

    # ------------------------------------------------------------------- 入口

    def pick(self) -> str | None:
        """独立运行：自己开事件循环、自己接管终端。"""
        assert self.app is not None
        try:
            return self.app.run()
        except (EOFError, KeyboardInterrupt):
            return None

    async def pick_async(self, host: Application | None = None) -> str | None:
        """异步运行；``host`` 给定时嵌到宿主应用里。

        嵌入模式不另起 Application，也不碰 stdin：临时把宿主的 layout /
        键位 / 样式换成 picker 的，让宿主自己的按键处理驱动它。这样就不存在
        “两个 Application 抢同一个终端和事件循环”的问题，宿主退出后也
        不需要重新 attach 输入。

        宿主一般是一个已经在运行的应用（比如 REPL 的 PromptSession），
        它的 layout 被暂时换掉、退出时再换回来。
        """
        assert self.app is not None
        if host is None:
            try:
                return await self.app.run_async()
            except (EOFError, KeyboardInterrupt):
                return None

        loop = asyncio.get_running_loop()
        result: asyncio.Future[str | None] = loop.create_future()
        saved_layout, saved_keys, saved_style = (
            host.layout,
            host.key_bindings,
            host.style,
        )

        self._host = host
        # _exit() 里调 app.exit()，把结果写进这个 future。
        self.app.future = result
        host.layout = self.app.layout
        host.key_bindings = self.app.key_bindings
        host.style = self.app.style
        host.invalidate()
        try:
            return await result
        finally:
            self._host = None
            self.app.future = None
            host.layout, host.key_bindings, host.style = (
                saved_layout,
                saved_keys,
                saved_style,
            )
            # 先把 picker 占用的行抹掉，再让宿主重画自己的界面。
            host.renderer.erase()
            host.invalidate()
