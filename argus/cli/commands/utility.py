
import argparse
from cmd2 import with_category, with_argparser, Cmd2ArgumentParser
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.box import SIMPLE_HEAVY

from argus.cli.views.table_modules import display_table
from argus.cli.logo import logo, TEAL
from argus.core.catalog_cache import number_of_modules, VERSION, AUTHOR

__mixin_name__ = "UtilityMixin"

console = Console()


def _header(txt: str) -> Panel:
    return Panel(Text(f" {txt} ", justify="center", style=f"bold white on {TEAL}"),
                 expand=False, padding=(0, 2), style=TEAL)


class UtilityMixin:

    @with_category("Utility")
    def do_clear(self, _line) -> None:
        from os import system, name as os_name
        system("cls" if os_name == "nt" else "clear")
        self._print_status_bar()

    @with_category("Utility")
    def do_banner(self, _line) -> None:
        console.print()
        logo()
        console.print()
        display_table()
        console.print()
        self._print_status_bar()

    @with_category("Utility")
    def do_info(self, _line) -> None:
        console.print()
        console.print(_header(" Argus Info "))
        console.print()
        tbl = Table(box=SIMPLE_HEAVY)
        tbl.add_column("Attr", style="cyan", no_wrap=True)
        tbl.add_column("Value", style="green")
        tbl.add_row("Version", VERSION)
        tbl.add_row("Author", AUTHOR)
        tbl.add_row("Modules", str(number_of_modules))
        tbl.add_row("Favorites", str(len(self.favorite_modules)))
        tbl.add_row("Recent", str(len(self.recent_modules)))
        tbl.add_row("Target", self.target or "Not set")
        tbl.add_row("Threads", str(self.threads))
        console.print(tbl)
        console.print()
        self._print_status_bar()

    @with_category("Configuration")
    def do_reset(self, _line) -> None:
        reset_type = _line.strip().lower()
        
        if reset_type == "favorites":
            count = len(self.favorite_modules)
            self.favorite_modules.clear()
            console.print()
            console.print(_header(" Favorites Reset "))
            console.print(Text(f"Cleared {count} favorites.", style="bold green"))
            console.print()
        elif reset_type == "recent":
            count = len(self.recent_modules)
            self.recent_modules.clear()
            console.print()
            console.print(_header(" Recent Reset "))
            console.print(Text(f"Cleared {count} recent modules.", style="bold green"))
            console.print()
        elif reset_type == "options":
            self.module_options.clear()
            self.global_option_overrides.clear()
            console.print()
            console.print(_header(" Options Reset "))
            console.print(Text("All options cleared.", style="bold green"))
            console.print()
        else:
            self.selected_module = None
            self.module_options.clear()
            self.global_option_overrides.clear()
            self.recent_modules.clear()
            self.last_search_results = []
            console.print()
            console.print(_header(" Full State Reset "))
            console.print(Text("CLI state completely cleared.", style="bold green"))
            console.print()
        
        self._print_status_bar()

    _config_parser = Cmd2ArgumentParser(description="Open configuration file")
    _config_parser.add_argument("editor", nargs="?", help="Specific editor to use")

    @with_argparser(_config_parser)
    @with_category("Configuration")
    def do_config(self, args) -> None:
        import subprocess
        import sys
        import os
        
        config_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.py")
        
        if not os.path.exists(config_file):
            self.perror(f"Config file not found at: {config_file}")
            return
        
        try:
            if sys.platform.startswith('win'):
                os.startfile(config_file)
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', config_file])
            else:
                subprocess.run(['xdg-open', config_file])
            console.print(Text("Config file opened in default editor.", style="bold green"))
        except Exception as e:
            self.perror(f"Failed to open config file: {e}")

    @with_category("Utility")
    def do_exit(self, _line) -> bool:
        console.print(Text("Exiting Argus. Goodbye!", style="bold green"))
        return True

    def do_quit(self, line):
        return self.do_exit(line)

    def do_EOF(self, line):
        return self.do_exit(line)
