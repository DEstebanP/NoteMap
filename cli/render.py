import os
import re

from rich.align import Align
from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from pygments.token import Keyword, Name, Number, String
from rich.style import Style
from rich.syntax import ANSI_DARK, ANSISyntaxTheme, Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from core.services import PHASES, OS_TYPES, Filters

THEME = Theme({
    "id": "dim",
    "os": "dim",
    "phase": "bold",
    "rule": "bright_black",
    "match": "bold red",
    "muted": "dim",
    "desc": "grey70",
    "note.label": "bold grey58",
    "title": "bold",
    "block": "bold",
    "ref": "bold",
    "label": "dim",
    "placeholder": "bold #af5fff",
    "code.tool": "bold",
    "code.flag": "#5fafff",
})

console = Console(theme=THEME)

MAX_WIDTH = 140
ID_WIDTH = 4
OS_WIDTH = max(len(os) for os in OS_TYPES)


def _new_table(show_header: bool = False) -> Table:
    # Same fixed widths on every table so columns line up across phases
    table = Table(show_header=show_header, header_style="muted", box=None, expand=True, pad_edge=False, padding=(0, 2))
    table.add_column("ID", style="id", width=ID_WIDTH, justify="right", no_wrap=True)
    table.add_column("Title", ratio=1, overflow="ellipsis", no_wrap=True)
    table.add_column("OS", style="os", width=OS_WIDTH, no_wrap=True)
    return table


def _phase_order(phase: str) -> int:
    return PHASES.index(phase) if phase in PHASES else len(PHASES)


def _describe_filters(filters: Filters) -> Text:
    # "smb enum · tag netexec, impacket · os linux"
    parts = []
    if filters.terms:
        parts.append(Text(" ".join(filters.terms), style="bold"))

    labeled = [
        ("tag", ", ".join(filters.tags or [])),
        ("phase", filters.phase),
        ("os", filters.os),
        ("machine", filters.machine),
    ]
    for label, value in labeled:
        if value:
            parts.append(Text.assemble((f"{label} ", "muted"), (value, "bold")))

    if not parts:
        return Text("all entries", style="muted")
    return Text("  ·  ", style="muted").join(parts)


def render_search_results(results, filters: Filters, console: Console = console):
    terms = filters.terms or []
    query = Text.assemble(("Search: ", "muted"), _describe_filters(filters))

    if not results:
        console.print(Text.assemble(("No results for: ", "muted"), _describe_filters(filters)))
        return

    # Everything goes inside one centered panel, capped at MAX_WIDTH
    parts = [_new_table(show_header=True)]

    phases = sorted({result.phase for result in results}, key=_phase_order)

    for phase in phases:
        parts.append(Rule(Text(phase.upper(), style="phase"), style="rule", align="left", characters="─"))

        table = _new_table()
        for result in (r for r in results if r.phase == phase):
            title = Text(result.title)
            title.highlight_words(terms, style="match", case_sensitive=False)
            table.add_row(str(result.id), title, result.os or "-")

        parts.append(table)

    count = Text(f"{len(results)} result{'s' if len(results) != 1 else ''}", style="muted")
    panel = Panel(
        Group(*parts),
        title=query, title_align="left",
        subtitle=count, subtitle_align="right",
        border_style="rule",
        padding=(1, 2),
        width=min(console.width, MAX_WIDTH),
    )
    console.print(Align.center(panel))


# ── Detail view (--show) ─────────────────────────────────────────────

MARGIN = 5   # empty columns on each side of the terminal
INDENT = 4   # extra indent for commands inside a block

# Regex for the fill-in markers inside commands. None = no highlighting.
PLACEHOLDER_PATTERN = r'(?i)<[A-Z]+>'

# Background of the code block (like a Notion code block)
CODE_BG = "grey15"

# Soft palette on top of ansi_dark (whose bright ANSI colours look loud).
# Keep it consistent with the THEME: flags blue, placeholders lavender.
_CODE_THEME = ANSISyntaxTheme({
    **ANSI_DARK,
    String: Style(color="#5fff87"),           # green
    Number: Style(color="#ffaf5f"),           # sand
    Name.Variable: Style(color="#ff5f87"),    # rose
    Keyword: Style(color="#af5fff", italic=True),
    Name.Builtin: Style(),                    # echo, cd... as plain text
})

_command_hl = Syntax("", "bash", theme=_CODE_THEME, background_color=CODE_BG)
_example_hl = Syntax("", "bash", theme=_CODE_THEME, background_color="default")

# Tool = first word of each line / after a pipe; flags = -x, --script
_TOOL_RE = r"(?m)(?:^|(?<=\|\s))[\w.\-]+"
_FLAG_RE = r"(?<!\S)--?[A-Za-z][\w-]*"


def _code(code: str, band: bool) -> Text:
    text = (_command_hl if band else _example_hl).highlight(code)
    text.rstrip()
    if band:
        text.highlight_regex(_TOOL_RE, style="code.tool")
        text.highlight_regex(_FLAG_RE, style="code.flag")
    if PLACEHOLDER_PATTERN:
        text.highlight_regex(PLACEHOLDER_PATTERN, style="placeholder")
    # Syntax.highlight() returns no_wrap=True: without this, long lines get cut
    text.no_wrap = False
    text.overflow = "fold"  # long paths/tokens break instead of being cut
    return text


def _code_block(code: str) -> Padding:
    # Padding with a background style fills the whole rectangle, blank
    # lines included. Multi-line scripts get vertical breathing room.
    v_pad = 1 if "\n" in code.strip() else 0
    return Padding(_code(code, band=True), (v_pad, 2), style=f"on {CODE_BG}", expand=True)


def _emit(out: Console, renderable, indent: int = 0):
    # Every line of the document goes through here: keeps the side margins
    out.print(Padding(renderable, (0, MARGIN, 0, MARGIN + indent)))


def _meta_line(detail) -> Text:
    parts = [Text(detail.phase, style="phase")]
    if detail.os:
        parts.append(Text(detail.os, style="os"))
    if detail.tags:
        parts.append(Text.assemble(("tags: ", "label"), ", ".join(t.name for t in detail.tags)))
    if detail.machines:
        parts.append(Text.assemble(("machines: ", "label"), ", ".join(m.name for m in detail.machines)))
    return Text("  ·  ", style="muted").join(parts)


def _ordered(items):
    # position may be NULL: those go last, keeping their original order
    return sorted(items, key=lambda i: (i.position is None, i.position or 0))


def _numbered(items) -> bool:
    # A level shows numbers only if the author gave it an order
    return any(i.position is not None for i in items)


def _heading(text: str, number: str | None) -> Group:
    # Terminals can't change font size: an "h2" is bold text + an underline
    # as long as the heading itself (like a setext Markdown heading).
    label = Text.assemble((f"{number}  ", "block") if number else "", (text, "block"))
    return Group(label, Text("─" * label.cell_len, style="rule"))


def _print_detail(out: Console, detail):
    # Header
    header = Table.grid(expand=True)
    header.add_column(ratio=1)
    header.add_column(justify="right")
    header.add_row(Text(detail.title, style="title"), Text(f"#{detail.id}", style="id"))
    out.print()
    _emit(out, header)
    _emit(out, _meta_line(detail))
    _emit(out, Rule(style="rule"))

    if detail.description:
        _emit(out, Text(detail.description))

    # Blocks → commands
    blocks = _ordered(detail.blocks)
    number_blocks = _numbered(blocks)
    for b_idx, block in enumerate(blocks, start=1):
        out.print()
        b_num = str(b_idx) if number_blocks else None
        _emit(out, _heading(block.title or f"Block {b_idx}", b_num))
        if block.description:
            _emit(out, Text(block.description, style="desc"))

        for cmd in _ordered(block.commands):
            out.print()
            _emit(out, _code_block(cmd.command), INDENT)
            if cmd.example:
                _emit(out, Text("↳ example", style="label"), INDENT)
                _emit(out, _code_block(cmd.example), INDENT)
            if cmd.note:
                # Hanging indent: wrapped lines align with the text, not the label
                note = Table.grid(padding=(0, 1))
                note.add_column(no_wrap=True)
                note.add_column(ratio=1)
                note.add_row(Text("✎ Note:", style="note.label"), Text(cmd.note, style="desc"))
                _emit(out, note, INDENT)

    if detail.notes:
        out.print()
        _emit(out, _heading("Notes", None))
        _emit(out, Text(detail.notes))

    out.print()
    _emit(out, Rule(style="rule"))


def render_entry_detail(detail, console: Console = console, pager: bool = True):
    out = Console(theme=THEME, width=console.width, file=console.file)
    if not pager:
        _print_detail(out, detail)
        return

    # less needs -R to interpret colours instead of showing raw escape codes
    os.environ.setdefault("LESS", "-R")
    with out.pager(styles=True):
        _print_detail(out, detail)


def render_entry_not_found(entry_id: int, console: Console = console):
    console.print(Text.assemble(("No entry with id ", "muted"), (str(entry_id), "bold")))
