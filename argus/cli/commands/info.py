from __future__ import annotations

import argparse
import re
from typing import List, Tuple

from cmd2 import with_argparser, with_category, Cmd2ArgumentParser
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from argus.cli.views.table_modules import module_info_table, display_table
from argus.cli.helpers import resolve_module_number, fuzzy_find_modules, regex_find_modules
from argus.core.catalog_cache import TOOL_TAGS, tools_mapping

__mixin_name__ = "InfoMixin"

TEAL = "#2EC4B6"
SECTION_COLOR = "magenta"
OK = "[green]✔[/green]"
NO = "[red]✘[/red]"

console = Console()


def _kv_block(pairs: List[Tuple[str, str | int | bool]]) -> Group:
    lines = []
    for k, v in pairs:
        t = Text()
        t.append(str(k).ljust(14), style="cyan")
        t.append(str(v), style="green")
        lines.append(t)
    return Group(*lines)


class InfoMixin:

    _show_parser = Cmd2ArgumentParser(description="Show things")
    _sub = _show_parser.add_subparsers(dest="what")
    for itm in ("modules", "options", "options_full", "api_status"):
        _sub.add_parser(itm)

    @with_argparser(_show_parser)
    @with_category("Information")
    def do_show(self, args) -> None:
        match args.what:
            case "modules":
                display_table()
            case "options":
                self._show_opts(full=False)
            case "options_full":
                self._show_opts(full=True)
            case "api_status":
                self._show_api_status()
        self._print_status_bar()

    @with_category("Information")
    def do_scope(self, _line) -> None:
        pairs: List[Tuple[str, str | int | bool]] = [
            ("Target", self.target or "—"),
            ("Threads", self.threads),
            ("Quiet", self.quiet_mode),
            ("Color", not self.no_color),
        ]
        if self.wrap_width:
            pairs.append(("Wrap width", self.wrap_width))
        pairs.extend(self.global_option_overrides.items())

        header = Text(" Current Scope ", justify="center", style=f"bold white on {TEAL}")
        console.print()
        console.print(Panel(_kv_block(pairs), title=header, border_style=TEAL, expand=False))
        console.print()
        self._print_status_bar()

    @with_category("Information")
    def do_recent(self, _line) -> None:
        if not self.recent_modules:
            self.pwarning("No recent modules.")
            return

        mods = [tools_mapping[mid] for mid in list(self.recent_modules)[::-1]]
        id_w = max(len(m["number"]) for m in mods) + 2
        name_w = max(len(m["name"]) for m in mods) + 2

        header = Text(" Recent Runs ", justify="center", style=f"bold white on {TEAL}")
        console.print()
        console.print(Panel(header, expand=False, padding=(0, 2), style=TEAL))
        console.print()

        titles = Text()
        titles.append("No.".ljust(4), style=f"bold {TEAL}")
        titles.append("ID".ljust(id_w), style="bold white")
        titles.append("Name".ljust(name_w), style="bold white")
        titles.append("Tags", style=f"bold {SECTION_COLOR}")
        console.print(titles)
        console.print()

        for idx, m in enumerate(mods, 1):
            tags = " ".join(f"[{tg}]" for tg in sorted(TOOL_TAGS[m["number"]]))
            line = Text()
            line.append(f"{idx}.".ljust(4), style=f"bold {TEAL}")
            line.append(m["number"].ljust(id_w), style="white")
            line.append(m["name"].ljust(name_w), style="white")
            line.append(tags, style=SECTION_COLOR)
            console.print(line)

        console.print()
        self._print_status_bar()

    @with_category("Information")
    def do_viewout(self, arg: str) -> None:
        key = arg.strip()
        if not self.last_run_outputs:
            self.pwarning("No cached output.")
            return

        panels = []
        for name, out in self.last_run_outputs.items():
            if not key or key.lower() in name.lower():
                panels.append(Panel(out, title=name, border_style="green", padding=(0, 1)))

        if not panels:
            self.pwarning("No cached output matched that key.")
            return

        console.print()
        console.print(Group(*panels))
        console.print()
        self._print_status_bar()

    _grep_parser = Cmd2ArgumentParser(description="Regex search in last output")
    _grep_parser.add_argument("pattern")
    _grep_parser.add_argument("--case-sensitive", action="store_true", help="case sensitive search")
    _grep_parser.add_argument("--count", action="store_true", help="show only count of matches")
    _grep_parser.add_argument("--module", help="search only in specific module output")

    @with_argparser(_grep_parser)
    @with_category("Information")
    def do_grepout(self, args) -> None:
        if not self.last_run_outputs:
            self.pwarning("No cached output.")
            return

        try:
            flags = 0 if args.case_sensitive else re.I
            rx = re.compile(args.pattern, flags)
        except re.error:
            self.perror("Invalid regex.")
            return

        hits: List[Tuple[str, str]] = []
        search_modules = [args.module] if args.module else self.last_run_outputs.keys()
        
        for name in search_modules:
            if name in self.last_run_outputs:
                out = self.last_run_outputs[name]
                hits.extend((name, ln) for ln in out.splitlines() if rx.search(ln))

        console.print()
        header = Text(f" Grep: {args.pattern} ", justify="center", style=f"bold white on {TEAL}")
        console.print(Panel(header, expand=False, padding=(0, 2), style=TEAL))
        console.print()

        if not hits:
            console.print(Text("No matches.", style="bold red"))
            console.print()
            self._print_status_bar()
            return

        if args.count:
            console.print(Text(f"Found {len(hits)} matches.", style="bold green"))
            console.print()
            self._print_status_bar()
            return

        mod_w = max(len(n) for n, _ in hits) + 2

        titles = Text()
        titles.append("Module".ljust(mod_w), style=f"bold {TEAL}")
        titles.append("Line", style="bold white")
        console.print(titles)
        console.print()

        for n, ln in hits:
            line = Text()
            line.append(n.ljust(mod_w), style="cyan")
            line.append(ln, style="green")
            console.print(line)

        console.print()
        self._print_status_bar()

    @with_category("Information")
    def do_helpmod(self, arg: str) -> None:
        ident = arg.strip() or (self.selected_module and self.selected_module["number"])
        if not ident:
            self.perror("helpmod <id|name>")
            return

        tool = self._resolve_by_any(ident)
        if not tool:
            self.perror("Module not found.")
            return

        opts = self.module_options.get(tool["number"], {})
        console.print()
        console.print(module_info_table(tool, self.target, self.threads, opts, show_full=True))
        console.print()
        self._print_status_bar()

    def do_hm(self, arg: str) -> None:
        self.do_helpmod(arg)

    _api_parser = Cmd2ArgumentParser(description="Manage API keys")
    _api_parser.add_argument("service", nargs="?", help="Service name or ID")
    _api_parser.add_argument("key", nargs="?", help="API key value")

    @with_argparser(_api_parser)
    @with_category("Configuration")
    def do_api(self, args) -> None:
        if not args.service:
            self._show_api_status()
            return
        
        if not args.key:
            self.perror("Usage: api <service|id> <key>")
            return
        
        if not args.key.strip():
            self.perror("API key cannot be empty.")
            return
        
        service_name = self._resolve_service_name(args.service)
        if not service_name:
            self.perror(f"Unknown service: {args.service}")
            return
        
        api_key_name = self._get_api_key_name(service_name)
        success = self._update_settings_file(api_key_name, args.key)
        
        if success:
            self.api_status[service_name] = True
            console.print()
            header = Text(f" API Key Set ", justify="center", style=f"bold white on {TEAL}")
            console.print(Panel(header, expand=False, padding=(0, 2), style=TEAL))
            console.print()
            console.print(Text(f"API key for {service_name} set successfully in settings.py", style="bold green"))
            console.print()
        else:
            self.perror(f"Failed to update settings.py for {service_name}")
            return
        
        self._show_api_status()

    def _show_opts(self, *, full: bool) -> None:
        if not self.selected_module:
            self.perror("No module selected.")
            return
        mid = self.selected_module["number"]
        opts = self.module_options.get(mid, {})
        console.print()
        console.print(module_info_table(self.selected_module, self.target, self.threads, opts, show_full=full))
        console.print()
        self._print_status_bar()

    def _resolve_service_name(self, service_input: str) -> str | None:
        expected_services = ["virustotal", "shodan", "google", "censys", "censys_secret", "ssl_labs", "hibp"]
        
        if service_input.isdigit():
            idx = int(service_input) - 1
            if 0 <= idx < len(expected_services):
                return expected_services[idx]
            return None
        
        if service_input.lower() in expected_services:
            return service_input.lower()
        
        return None

    def _get_api_key_name(self, service: str) -> str:
        api_key_mapping = {
            "virustotal": "VIRUSTOTAL_API_KEY",
            "shodan": "SHODAN_API_KEY", 
            "google": "GOOGLE_API_KEY",
            "censys": "CENSYS_API_ID",
            "censys_secret": "CENSYS_API_SECRET",
            "ssl_labs": "SSL_LABS_API_KEY",
            "hibp": "HIBP_API_KEY"
        }
        return api_key_mapping.get(service, f"{service.upper()}_API_KEY")

    def _update_settings_file(self, api_key_name: str, api_key_value: str) -> bool:
        import os
        import re
        
        config_file = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.py")
        
        if not os.path.exists(config_file):
            return False
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            pattern = rf'"{api_key_name}":\s*os\.getenv\("{api_key_name}",\s*"[^"]*"\)'
            replacement = f'"{api_key_name}": os.getenv("{api_key_name}", "{api_key_value}")'
            
            if re.search(pattern, content):
                new_content = re.sub(pattern, replacement, content)
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
            else:
                return False
                
        except Exception as e:
            console.print(f"Error updating settings: {e}", style="red")
            return False

    def _show_api_status(self) -> None:
        expected_services = ["virustotal", "shodan", "google", "censys", "censys_secret", "ssl_labs", "hibp"]
        svc_w = max(len(k) for k in expected_services) + 2

        header = Text(" API Status ", justify="center", style=f"bold white on {TEAL}")
        console.print()
        console.print(Panel(header, expand=False, padding=(0, 2), style=TEAL))
        console.print()

        titles = Text()
        titles.append("ID".ljust(4), style=f"bold {TEAL}")
        titles.append("Service".ljust(svc_w), style=f"bold {TEAL}")
        titles.append("Status", style="bold white")
        console.print(titles)
        console.print()

        for i, service in enumerate(expected_services, 1):
            api_key_name = self._get_api_key_name(service)
            configured = self.api_status.get(service, False)
            
            display_name = service.replace("_", " ").title()
            if service == "censys_secret":
                display_name = "Censys Secret"
            elif service == "ssl_labs":
                display_name = "SSL Labs"
            
            line = Text()
            line.append(f"{i}".ljust(4), style=f"bold {TEAL}")
            line.append(display_name.ljust(svc_w), style="white")
            if configured:
                line.append("✔", style="green")
            else:
                line.append("✘", style="red")
            console.print(line)

        console.print()
        console.print(Text("Usage: api <service|id> <key>", style="dim"))
        console.print()
        self._print_status_bar()
