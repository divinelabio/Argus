from __future__ import annotations
import argparse, types
from typing import List
from cmd2 import with_argparser, with_category, Cmd2ArgumentParser
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from argus.cli.helpers import (
    resolve_module_number,
    fuzzy_find_modules,
    numeric_or_warn,
    suggest_option_name,
    ALL_KNOWN_MODULE_OPTIONS,
    NUMERIC_OPTION_HINTS,
)
from argus.cli.views.table_modules import module_info_table
from argus.core.catalog_cache import tools_mapping

__mixin_name__ = "SelectMixin"
TEAL = "#2EC4B6"
console = Console()

def _flash(msg: str, level: str = "info") -> None:
    style = {
        "ok": "bold green",
        "info": "cyan",
        "warn": "bold yellow",
        "err": "bold red",
    }.get(level, "cyan")
    console.print(msg, style=style)

class SelectMixin:
    _use_parser = Cmd2ArgumentParser(description="Select a module")
    _use_parser.add_argument("identifier", help="ID | Tmp# | name fragment")

    @with_argparser(_use_parser)
    @with_category("Module Management")
    def do_use(self, args) -> None:
        ident = args.identifier
        if self.last_search_results and ident.isdigit():
            idx = int(ident) - 1
            if 0 <= idx < len(self.last_search_results):
                self.selected_module = self.last_search_results[idx]
                self.last_search_results = []
                self._announce_selected()
                return
        if ident.isdigit():
            resolved = resolve_module_number(ident)
            if resolved:
                self.selected_module = tools_mapping[resolved]
                self._announce_selected()
                return
        matches = fuzzy_find_modules(ident)
        if not matches:
            _flash(f"[!] No module matched '{ident}'.", "err")
            return
        if len(matches) == 1:
            self.selected_module = matches[0]
            self._announce_selected()
            return
        id_w = max(len(m["number"]) for m in matches) + 2
        name_w = max(len(m["name"]) for m in matches) + 2
        header = Text(" Multiple Matches ", justify="center", style=f"bold white on {TEAL}")
        console.print()
        console.print(Panel(header, expand=False, padding=(0, 2), style=TEAL))
        console.print()
        titles = Text()
        titles.append("Tmp#".ljust(6), style=f"bold {TEAL}")
        titles.append("ID".ljust(id_w), style="bold white")
        titles.append("Name".ljust(name_w), style="bold white")
        console.print(titles)
        console.print()
        for i, m in enumerate(matches, 1):
            line = Text()
            line.append(f"{i}".ljust(6), style=f"bold {TEAL}")
            line.append(m["number"].ljust(id_w), style="white")
            line.append(m["name"].ljust(name_w), style="white")
            console.print(line)
        console.print()
        self.last_search_results = matches
        self._print_status_bar()

    def _announce_selected(self) -> None:
        mid = self.selected_module["number"]
        opts = self.module_options.get(mid, {})
        console.print()
        header = Text(f" Selected: {self.selected_module['name']} ", justify="center", style=f"bold white on {TEAL}")
        console.print(Panel(header, expand=False, padding=(0, 2), style=TEAL))
        console.print()
        console.print(module_info_table(self.selected_module, self.target, self.threads, opts, show_full=True))
        console.print()
        self._print_status_bar()

    _set_parser = Cmd2ArgumentParser(description="Set target/threads/option")
    _set_parser.add_argument("tokens", nargs="+", help="Flexible setter syntax")

    @with_argparser(_set_parser)
    @with_category("Configuration")
    def do_set(self, args) -> None:
        self._handle_tokens(args.tokens)

    _unset_parser = Cmd2ArgumentParser(description="Unset an option")
    _unset_parser.add_argument("tokens", nargs="+", help="opt | id opt")

    @with_argparser(_unset_parser)
    @with_category("Configuration")
    def do_unset(self, args) -> None:
        toks = args.tokens
        if len(toks) == 1:
            key = toks[0].replace("-", "_").lower()
            if key in self.global_option_overrides:
                del self.global_option_overrides[key]
                _flash(f"[+] global option removed: {key}", "ok")
            else:
                _flash("[-] that global option was not set.", "warn")
            return
        if len(toks) == 2 and toks[0].isdigit():
            mid = resolve_module_number(toks[0])
            key = toks[1].replace("-", "_").lower()
            if mid and mid in self.module_options and key in self.module_options[mid]:
                del self.module_options[mid][key]
                _flash(f"[+] module {mid} option removed: {key}", "ok")
            else:
                _flash("[-] that option was not set for that module.", "warn")
            return
        _flash("invalid unset usage.", "err")

    @with_category("Information")
    def do_opts(self, line: str) -> None:
        ident = line.strip()
        if ident:
            mod = None
            if ident.isdigit():
                resolved = resolve_module_number(ident)
                mod = tools_mapping.get(resolved) if resolved else None
            else:
                matches = fuzzy_find_modules(ident)
                mod = matches[0] if len(matches) == 1 else None
            if not mod:
                _flash("module not found", "err")
                return
        else:
            if not self.selected_module:
                _flash("no module selected.", "err")
                return
            mod = self.selected_module
        mid = mod["number"]
        opts = self.module_options.get(mid, {})
        console.print()
        console.print(module_info_table(mod, self.target, self.threads, opts, show_full=True))
        console.print()
        self._print_status_bar()

    def _set_option_for_module(self, mid: str, key: str, value: str) -> None:
        k_norm = key.replace("-", "_").lower()
        if k_norm in NUMERIC_OPTION_HINTS and not numeric_or_warn(k_norm, value):
            _flash(f"option '{k_norm}' expects numeric value.", "err")
            return
        self.module_options.setdefault(mid, {})[k_norm] = value
        _flash(f"[+] module {mid} | {k_norm} = {value}", "ok")

    def _set_any(self, key: str, value: str) -> None:
        k_norm = key.replace("-", "_").lower()
        if k_norm == "target":
            if not value or len(value.strip()) == 0:
                _flash("target cannot be empty.", "err")
                return
            self.target = value.strip()
            _flash(f"[+] Target set to: {self.target} \n", "ok")
            return
        if k_norm == "threads":
            if value.isdigit() and int(value) >= 1:
                thread_count = int(value)
                if thread_count > 100:
                    _flash(f"[!] high thread count ({thread_count}) may impact performance.", "warn")
                self.threads = thread_count
                _flash(f"[+] threads set to: {self.threads}", "ok")
                return
            _flash("threads must be >= 1.", "err")
            return
        if not self.selected_module:
            self._set_global_option(k_norm, value)
            return
        allowed = [o.replace("-", "_").lower() for o in (self.selected_module.get("options_meta") or [])]
        if k_norm not in allowed:
            sug = suggest_option_name(k_norm, allowed)
            if sug:
                _flash(f"unknown option. did you mean '{sug}'?", "warn")
            else:
                _flash(f"option not valid for {self.selected_module['name']}. allowed: {', '.join(allowed) or 'none'}", "warn")
            return
        if k_norm in NUMERIC_OPTION_HINTS and not numeric_or_warn(k_norm, value):
            _flash(f"option '{k_norm}' expects numeric value.", "err")
            return
        mid = self.selected_module["number"]
        self.module_options.setdefault(mid, {})[k_norm] = value
        _flash(f"[+] option set: {k_norm} = {value}", "ok")

    def _set_global_option(self, key: str, value: str) -> None:
        if key not in ALL_KNOWN_MODULE_OPTIONS:
            _flash(f"'{key}' is not a known global module option (will be saved anyway).", "warn")
        self.global_option_overrides[key] = value
        _flash(f"[+] global option set: {key} = {value}", "ok")

    def _handle_tokens(self, tokens: List[str]) -> None:
        if len(tokens) == 1 and "=" in tokens[0]:
            k, v = tokens[0].split("=", 1)
            self._set_any(k, v)
            return
        if len(tokens) == 2 and tokens[0] in {"target", "threads"}:
            self._set_any(tokens[0], tokens[1])
            return
        if tokens[0].isdigit() and len(tokens) >= 3:
            mid = resolve_module_number(tokens[0])
            if mid:
                self._set_option_for_module(mid, tokens[1], " ".join(tokens[2:]))
                return
            _flash("unknown module id.", "err")
            return
        if len(tokens) >= 2:
            self._set_any(tokens[0], " ".join(tokens[1:]))
            return
        _flash("invalid syntax.", "err")

    def default(self, line: str) -> None:
        toks = line.strip().split()
        if not toks:
            return super().default(line)
        if toks[0] in {"set", "unset", "use", "opts"}:
            return super().default(line)
        if toks[0].isdigit() and len(toks) >= 3:
            mid = resolve_module_number(toks[0])
            if mid:
                self._set_option_for_module(mid, toks[1], " ".join(toks[2:]))
                return
        if "=" in toks[0]:
            k, v = toks[0].split("=", 1)
            self._set_any(k, v)
            return
        if len(toks) >= 2:
            self._set_any(toks[0], " ".join(toks[1:]))
            return
        key = toks[0].replace("-", "_").lower()
        if key == "threads":
            _flash(f"[i] threads = {self.threads}", "info")
            return
        if key == "target":
            _flash(f"[i] target = {self.target}", "info")
            return
        if key in ALL_KNOWN_MODULE_OPTIONS:
            mid = self.selected_module["number"] if self.selected_module else None
            val = self.module_options.get(mid, {}).get(key) if mid else self.global_option_overrides.get(key)
            _flash(f"[i] {key} = {val}", "info")
            return
        super().default(line)

    def __getattr__(self, name: str):
        if name.startswith("do_"):
            opt = name[3:].replace("_", "-")
            if opt in {"target", "threads"} or opt in ALL_KNOWN_MODULE_OPTIONS:
                def dynamic_cmd(self, arg):
                    arg = arg.strip()
                    if arg:
                        self._handle_tokens([opt] + arg.split())
                    else:
                        key = opt.replace("-", "_")
                        if opt == "target":
                            _flash(f"[i] target = {self.target}", "info")
                        elif opt == "threads":
                            _flash(f"[i] threads = {self.threads}", "info")
                        else:
                            mid = self.selected_module["number"] if self.selected_module else None
                            val = self.module_options.get(mid, {}).get(key) if mid else self.global_option_overrides.get(key)
                            _flash(f"[i] {key} = {val}", "info")
                meth = types.MethodType(dynamic_cmd, self)
                setattr(self, name, meth)
                return meth
        raise AttributeError(name)

    def _show_opts_table(self) -> None:
        if not self.selected_module:
            self._print_status_bar()
            return
        mid = self.selected_module["number"]
        opts = self.module_options.get(mid, {})
        console.print()
        console.print(module_info_table(self.selected_module, self.target, self.threads, opts, show_full=True))
        console.print()
        self._print_status_bar()
