from typing import List

import argparse
from cmd2 import with_argparser, with_category, Cmd2ArgumentParser

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from argus.cli.views.table_modules import display_table
from argus.cli.helpers import fuzzy_find_modules, regex_find_modules
from argus.core.catalog_cache import (
    SECTION_TOOL_NUMBERS,
    SECTION_NAMES,
    TOOL_TAGS,
)

__mixin_name__ = "BrowseMixin"
TEAL = "#2EC4B6"
SECTION_COLOR = "magenta"

class BrowseMixin:

    @with_category("Module Browse")
    def do_modules(self, arg: str) -> None:
        a = (arg or "").strip().lower()

        short = "-s" in a
        details = "-d" in a
        show_tags = "-t" in a
        for sw in ("-s", "-d", "-t"):
            a = a.replace(sw, "").strip()

        section_filter = None
        tag_filter = None
        if a.startswith("infra"):
            section_filter = SECTION_NAMES["network_infrastructure"]
        elif a.startswith("web"):
            section_filter = SECTION_NAMES["web_application_analysis"]
        elif a.startswith("sec"):
            section_filter = SECTION_NAMES["security_threat_intelligence"]
        elif a.startswith("tag:"):
            tag_filter = a.split(":", 1)[1]

        console = Console()
        console.print()
        display_table(
            section_filter=section_filter,
            tag_filter=tag_filter,
            short=short,
            show_tags=show_tags,
            details=details,
        )
        console.print()
        self._print_status_bar()

    _search_parser = Cmd2ArgumentParser(description="Search for modules")
    _search_parser.add_argument("keyword", help="keyword to search")
    _search_parser.add_argument("--exact", action="store_true", help="exact match only")
    _search_parser.add_argument("--case-sensitive", action="store_true", help="case sensitive search")

    @with_argparser(_search_parser)
    @with_category("Module Browse")
    def do_search(self, args) -> None:
        keyword = args.keyword
        if args.case_sensitive:
            keyword = keyword.lower()
        
        if args.exact:
            matches = [m for m in fuzzy_find_modules("") if keyword in m["name"].lower()]
        else:
            matches: List = fuzzy_find_modules(keyword)
        console = Console()

        console.print()
        header = Text(f"Search: '{keyword}' ", justify="center", style=f"bold white on {TEAL}")
        console.print(Panel(header, expand=False, padding=(0, 2), style=TEAL))
        console.print()

        if not matches:
            console.print(f":mag_right: No modules matched '{keyword}'", style="bold red")
            console.print()
            self._print_status_bar()
            return

        if len(matches) == 1:
            self._show_helpmod_tool(matches[0])
            console.print()
            self._print_status_bar()
            return

        id_width = max(len(tool['number']) for tool in matches) + 2
        name_width = max(len(tool['name']) for tool in matches) + 2

        cols = Text()
        cols.append("No.".ljust(4), style=f"bold {TEAL}")
        cols.append("ID".ljust(id_width), style="bold white")
        cols.append("Name".ljust(name_width), style="bold white")
        cols.append("Section", style=f"bold {SECTION_COLOR}")
        console.print(cols)
        console.print()

        for idx, tool in enumerate(matches, 1):
            line = Text()
            line.append(f"{idx}.".ljust(4), style=f"bold {TEAL}")
            line.append(tool['number'].ljust(id_width), style="white")
            line.append(tool['name'].ljust(name_width), style="white")
            line.append(tool['section'], style=SECTION_COLOR)
            console.print(line)

        console.print()
        console.print(Text(" Use '<No.>' or '<ID>' with 'use' to select ", style=f"bold white on {TEAL}"))
        console.print()

        self.last_search_results = matches
        self._print_status_bar()

    _searchre_parser = Cmd2ArgumentParser(description="Regex search modules")
    _searchre_parser.add_argument("pattern", help="Regular expression")

    @with_argparser(_search_parser)
    @with_category("Module Browse")
    def do_search(self, args) -> None:
        keyword = args.keyword.strip().lower()
        console = Console()

        fuzzy_hits: List = fuzzy_find_modules(keyword)

        direct_hits = [
            m for m in fuzzy_hits
            if keyword in m["name"].lower()
            or keyword in m.get("description","").lower()
            or any(keyword in t.lower() for t in m.get("tags", []))
        ]
        matches = direct_hits or fuzzy_hits

        console.print()
        header = Text(f"Search: '{args.keyword}' ", justify="center",
                    style=f"bold white on {TEAL}")
        console.print(Panel(header, expand=False, padding=(0, 2), style=TEAL))
        console.print()

        if not matches:
            console.print(f":mag_right: No modules matched '{args.keyword}'",
                        style="bold red")
            console.print()
            self._print_status_bar()
            return

        if len(matches) == 1:
            self._show_help_tool(matches[0])
            console.print()
            self._print_status_bar()
            return

        id_w   = max(len(t["number"]) for t in matches) + 2
        name_w = max(len(t["name"])   for t in matches) + 2

        cols = Text()
        cols.append("No.".ljust(4),             style=f"bold {TEAL}")
        cols.append("ID".ljust(id_w),           style="bold white")
        cols.append("Name".ljust(name_w),       style="bold white")
        cols.append("Section",                  style=f"bold {SECTION_COLOR}")
        console.print(cols); console.print()

        for idx, tool in enumerate(matches, 1):
            row = Text()
            row.append(f"{idx}.".ljust(4),      style=f"bold {TEAL}")
            row.append(tool["number"].ljust(id_w), style="white")
            row.append(tool["name"].ljust(name_w), style="white")
            row.append(tool["section"],            style=SECTION_COLOR)
            console.print(row)

        console.print()
        console.print(Text(" Use '<No.>' or '<ID>' with 'use' to select ",
                        style=f"bold white on {TEAL}"))
        console.print()

        self.last_search_results = matches
        self._print_status_bar()
