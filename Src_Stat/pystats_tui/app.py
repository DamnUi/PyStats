"""PyStats TUI application built with Textual.

Run with:
    python -m pystats_tui            (from Src_Stat)
    python -m pystats_tui -df <path> [--vars N] [--adhd]
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, HorizontalScroll, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

import _PyStats
from _PyStats import PyStatsConfig, Stat


class StatCard(Static):
    """A small labelled metric card used in the Overview strip."""

    DEFAULT_CSS = """
    StatCard {
        width: 1fr;
        height: auto;
        border: round $primary;
        padding: 0 1;
        content-align: center middle;
        text-style: bold;
    }
    """

    def __init__(self, title: str) -> None:
        super().__init__(f"{title}\n-", id=f"card-{title.lower().replace(' ', '-')}")
        self.card_title = title

    def set_value(self, value) -> None:
        self.update(f"{self.card_title}\n[b]{value}[/]")


class FilesTree(Tree):
    """Tree of discovered python files with sizes."""

    def load_files(self, file_paths: list[str], removed_files: list[str]) -> None:
        self.clear()
        self.root.label = f"Python files ({len(file_paths)})"
        for path in sorted(file_paths, key=lambda p: -os.path.getsize(p) if os.path.exists(p) else 0):
            try:
                size_kb = round(os.path.getsize(path) / 1000, 2)
            except OSError:
                size_kb = 0
            self.root.add(f"{path} [spring_green4]({size_kb} kB)[/]")
        if removed_files:
            removed_node = self.root.add("[bright_black]Removed (invalid syntax)[/]")
            for path in removed_files:
                removed_node.add(f"[bright_black]{path}[/]")
        self.root.expand()


class HelpScreen(ModalScreen[None]):
    """Keyboard shortcuts help."""

    BINDINGS = [("escape", "dismiss", "Close")] + [("question_mark", "dismiss", "Close")]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-panel {
        width: 60;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            "[b]PyStats Keyboard Shortcuts[/]\n\n"
            "[b]q[/]        Quit\n"
            "[b]tab[/]      Next tab / focus next\n"
            "[b]r[/]        Reload statistics\n"
            "[b]s[/]        Save dashboard SVG (PyStats.svg)\n"
            "[b]?[/]        Show this help\n"
            "[b]escape[/]   Close this help",
            id="help-panel",
        )

    def action_dismiss(self, event=None) -> None:
        self.dismiss(None)


class PyStatsApp(App[None]):
    """The PyStats Textual application."""

    TITLE = "PyStats - Python Code Statistics"
    SUB_TITLE = "powered by Textual"

    CSS = """
    Screen {
        layers: base;
    }
    #metric-strip {
        height: auto;
        margin: 0 0 1 0;
    }
    #main-tabs {
        height: 1fr;
    }
    TabPane {
        padding: 0 1;
    }
    #files-tree {
        width: 40%;
        border: round $primary;
    }
    #files-detail {
        width: 1fr;
        border: round $secondary;
        padding: 0 1;
    }
    DataTable {
        height: 1fr;
    }
    #loading-bar {
        display: none;
    }
    #loading-bar.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "reload", "Reload"),
        Binding("s", "save_svg", "Save SVG"),
        Binding("question_mark", "help", "Help"),
    ]

    def __init__(self, config: PyStatsConfig) -> None:
        super().__init__()
        self.config = config
        self.stat: Optional[Stat] = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="metric-strip"):
            yield StatCard("Files")
            yield StatCard("Lines")
            yield StatCard("Avg Lines")
            yield StatCard("Classes")
            yield StatCard("Functions")
            yield StatCard("Variables")
        with TabbedContent(id="main-tabs"):
            with TabPane("Files"):
                with Horizontal():
                    yield FilesTree("Files", id="files-tree")
                    yield Static("Select a file...", id="files-detail")
            with TabPane("Lines & Dupes"):
                yield DataTable(id="table-lines")
            with TabPane("Imports"):
                yield DataTable(id="table-imports")
            with TabPane("Functions"):
                yield DataTable(id="table-functions")
            with TabPane("Classes"):
                yield DataTable(id="table-classes")
            with TabPane("Variables"):
                yield DataTable(id="table-variables")
            with TabPane("Statements"):
                yield Static(id="statements-view", markup=True)
            with TabPane("Decorators"):
                yield DataTable(id="table-decorators")
        yield ProgressBar(total=100, show_eta=False, id="loading-bar")
        yield Footer()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def on_mount(self) -> None:
        self.load_stats()

    def load_stats(self) -> None:
        loading = self.query_one("#loading-bar", ProgressBar)
        loading.add_class("visible")
        loading.progress = 10

        working = self.config.working_path
        self.stat = Stat(working, config=self.config)

        loading.progress = 40
        self.populate_metric_strip()
        loading.progress = 60
        self.populate_files_tab()
        self.populate_lines_tab()
        loading.progress = 75
        self.populate_imports_tab()
        self.populate_functions_tab()
        loading.progress = 90
        self.populate_classes_tab()
        self.populate_variables_tab()
        self.populate_statements_tab()
        self.populate_decorators_tab()
        loading.progress = 100
        loading.remove_class("visible")
        self.set_loading_progress(None)

    def set_loading_progress(self, value) -> None:
        pass  # hook for future async loading

    # ------------------------------------------------------------------
    # Metric strip
    # ------------------------------------------------------------------
    def populate_metric_strip(self) -> None:
        assert self.stat is not None
        lines = self.stat.line_count()
        avg = lines.pop("Average", 0)
        classes = self.stat.get_classes()
        _names, called = self.stat.most_called_func()
        variables = self.stat.most_used_variable(100000)

        cards = {
            "Files": len(self.stat.directory),
            "Lines": sum(lines.values()),
            "Avg Lines": avg,
            "Classes": len(classes),
            "Functions": len(called),
            "Variables": len(variables),
        }
        for title, value in cards.items():
            self.query_one(f"#card-{title.lower().replace(' ', '-')}", StatCard).set_value(value)

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------
    def populate_files_tab(self) -> None:
        tree = self.query_one("#files-tree", FilesTree)
        tree.load_files(self.stat.directory, self.config.removed_files)

    def populate_lines_tab(self) -> None:
        table = self.query_one("#table-lines", DataTable)
        table.clear(columns=True)
        table.add_columns("File", "Lines", "Empty-excluded")
        lines_all = self.stat.line_count()
        lines_nonempty = self.stat.line_count(exclude_empty_line=True)
        avg_all = lines_all.pop("Average", 0)
        avg_nonempty = lines_nonempty.pop("Average", 0)
        for path, count in lines_all.items():
            ne = lines_nonempty.get(path, "-")
            table.add_row(path, str(count), str(ne))
        table.add_row("[b]Average[/]", str(avg_all), str(avg_nonempty))

        # dupe lines as a second section, appended to same table? keep simple:
        dupes = self.stat.dupelinefind()
        top_dupes = list(dupes.items())[:5]
        if top_dupes:
            table.add_row("", "", "")
            table.add_row("[b]Most duplicated lines[/]", "count", "")
            for line, count in top_dupes:
                preview = (line[:60] + "...") if len(line) > 60 else line
                table.add_row(preview or "(blank)", str(count), "")

    def populate_imports_tab(self) -> None:
        table = self.query_one("#table-imports", DataTable)
        table.clear(columns=True)
        table.add_columns("Import", "Count")
        imports = self.stat.import_count()
        for key, value in imports.items():
            if isinstance(value, dict):
                value = sum(value.values())
            table.add_row(key, str(value))

    def populate_functions_tab(self) -> None:
        table = self.query_one("#table-functions", DataTable)
        table.clear(columns=True)
        table.add_columns("Function", "Times Called", "Line", "File")
        funcs = self.stat.get_func()
        for name, info in funcs.items():
            # info = ["useless", "display", file, line, times]
            _tag, display, file, line, times = info
            clean = display.replace("[cyan]", "").replace("[/]", "")
            table.add_row(clean, times, line, file)

    def populate_classes_tab(self) -> None:
        table = self.query_one("#table-classes", DataTable)
        table.clear(columns=True)
        table.add_columns("Class", "Details")
        classes = self.stat.get_classes()
        for name, details in classes.items():
            clean = details.replace("[red]", "").replace("[/]", "").replace(",", "\n")
            table.add_row(name, clean)

    def populate_variables_tab(self) -> None:
        table = self.query_one("#table-variables", DataTable)
        table.clear(columns=True)
        table.add_columns("Variable", "Uses", "Type")
        types = self.stat.get_var_types()
        variables = self.stat.most_used_variable(100000)
        combined = {}
        for name, count in variables.items():
            combined[name] = (count, types.get(name, "?"))
        for name, (count, var_type) in sorted(combined.items(), key=lambda kv: -kv[1][0]):
            table.add_row(name, str(count), var_type)

    def populate_statements_tab(self) -> None:
        view = self.query_one("#statements-view", Static)
        if_s, while_s, for_s, with_s, try_s, nvars = self.stat.get_control_statements()
        bar = lambda label, n, total: (
            f"[b]{label}[/] {n:>4}  " + "█" * max(int(n / total * 30), 1 if n else 0)
        )
        total = max(if_s + while_s + for_s + with_s + try_s, 1)
        view.update(
            "[b]Control flow statements[/]\n\n"
            + bar("if    ", if_s, total) + "\n"
            + bar("while ", while_s, total) + "\n"
            + bar("for   ", for_s, total) + "\n"
            + bar("with  ", with_s, total) + "\n"
            + bar("try   ", try_s, total) + "\n\n"
            + f"[b]Total defined variables:[/] {nvars}"
        )

    def populate_decorators_tab(self) -> None:
        table = self.query_one("#table-decorators", DataTable)
        table.clear(columns=True)
        table.add_columns("Decorator", "Count")
        decorators = self.stat.count_decorator()
        for name, count in sorted(decorators.items(), key=lambda kv: -kv[1]):
            table.add_row(name, str(count))

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------
    def on_tree_node_highlight(self, event: Tree.NodeHighlight) -> None:
        """Show file info when a file is highlighted in the tree."""
        label = str(event.node.label)
        detail = self.query_one("#files-detail", Static)
        # extract path portion before the size annotation
        path = label.split(" (")[0].strip()
        if os.path.isfile(path):
            try:
                size_kb = round(os.path.getsize(path) / 1000, 2)
                with open(path, encoding="utf-8") as f:
                    n_lines = sum(1 for _ in f)
                detail.update(
                    f"[b]{path}[/]\n\n"
                    f"Size: {size_kb} kB\n"
                    f"Lines: {n_lines}"
                )
            except OSError as e:
                detail.update(f"[b]{path}[/]\n\n[red]{e}[/]")
        else:
            detail.update(label)

    def action_reload(self) -> None:
        self.config = PyStatsConfig(sys.argv[1:])
        self.load_stats()

    def action_save_svg(self) -> None:
        """Save an SVG screenshot of the current screen (Textual export)."""
        try:
            data = self.export_screenshot()
            with open("PyStats.svg", "w", encoding="utf-8") as f:
                f.write(data)
            self.notify("Saved PyStats.svg", severity="information")
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())


def main() -> None:
    config = PyStatsConfig(sys.argv[1:])
    app = PyStatsApp(config)
    app.run()


if __name__ == "__main__":
    main()
