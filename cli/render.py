from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
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
