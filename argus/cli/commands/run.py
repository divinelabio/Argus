from __future__ import annotations

import argparse
from typing import List

from cmd2 import with_argparser, with_category, Cmd2ArgumentParser
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from argus.core.runner import run_modules
from argus.cli.helpers import resolve_module_number, fuzzy_find_modules
from argus.core.catalog_cache import SECTION_TOOL_NUMBERS, tools_mapping 

__mixin_name__ = "RunMixin"

TEAL = "#2EC4B6"
console = Console()


class RunMixin:
    _run_parser = Cmd2ArgumentParser(description="Run modules")
    _run_parser.add_argument("ids", nargs="*", help="[module ids] or target override")
    _run_parser.add_argument("--background", action="store_true")
    _run_parser.add_argument("--dry-run", action="store_true", help="show what would be run without executing")
    _run_parser.add_argument("--continue-on-error", action="store_true", help="continue running other modules if one fails")

    @with_argparser(_run_parser)
    @with_category("Execution")
    def do_run(self, args) -> None:
        ids: List[str] = args.ids

        if args.dry_run:
            if ids:
                mod_ids, target_override = self._parse_run_tokens(ids)
                if not mod_ids:
                    self.perror("No valid module ids supplied.")
                    return
                console.print(f"[yellow]DRY RUN: Would execute {len(mod_ids)} modules[/yellow]")
                for mid in mod_ids:
                    mod = tools_mapping.get(mid)
                    if mod:
                        console.print(f"  - {mid}: {mod['name']}")
                return
            else:
                if not self.selected_module:
                    self.perror("No module selected.")
                    return
                console.print(f"[yellow]DRY RUN: Would execute {self.selected_module['name']}[/yellow]")
                return

        if ids:
            mod_ids, target_override = self._parse_run_tokens(ids)
            if not mod_ids:
                self.perror("No valid module ids supplied.")
                return
            if target_override:
                self.target = target_override
            if not self.target:
                self._prompt_target_if_needed()
            self._invoke_runner(mod_ids, mode_name="CHAIN")
            return

        if not self.selected_module:
            self.perror("No module selected.")
            return

        if not self.target:
            self._prompt_target_if_needed()
        self._invoke_single(self.selected_module)

    def _parse_run_tokens(self, tokens: List[str]) -> tuple[List[str], str | None]:
        mod_ids: List[str] = []
        target_override = None
        for tok in tokens:
            if "." in tok and not tok.isdigit() and target_override is None:
                target_override = tok
                continue
            rid = resolve_module_number(tok) if tok.isdigit() else None
            if rid:
                mod_ids.append(rid)
                continue
            match = fuzzy_find_modules(tok)
            if match:
                mod_ids.append(match[0]["number"])
        return mod_ids, target_override

    def _invoke_runner(self, mod_ids: List[str], mode_name: str) -> None:
        
        run_modules(mod_ids, self.api_status, self.target, self.threads, mode_name, self)

    def _invoke_single(self, module: dict) -> None:
        self._invoke_runner([module["number"]], mode_name=module["name"])

    _runall_parser = Cmd2ArgumentParser(description="Run all modules in category")
    _runall_parser.add_argument("category", choices=["infrastructure", "web", "security"])

    @with_argparser(_runall_parser)
    @with_category("Execution")
    def do_runall(self, args) -> None:
        cat_map = {
            "infrastructure": "Network & Infrastructure",
            "web": "Web Application Analysis",
            "security": "Security & Threat Intelligence",
        }
        category = cat_map[args.category]
        mod_ids = SECTION_TOOL_NUMBERS.get(category, [])
        if not mod_ids:
            self.perror("No modules in that category.")
            return
        if not self.target:
            self._prompt_target_if_needed()
        self._invoke_runner(mod_ids, mode_name=f"ALL_{args.category.upper()}")

    @with_category("Execution")
    def do_runfav(self, _line) -> None:
        self._fav_run()

    @with_category("Execution")
    def do_last(self, _line) -> None:
        if not self.last_run_outputs:
            self.perror("Nothing has been run yet.")
            return
        if not self.selected_module:
            self.perror("Select a module first.")
            return
        self.do_run(argparse.Namespace(ids=[], background=False))

    def _run_all_selection(self) -> None:
        sel = self.selected_module
        if "Infrastructure" in sel["name"]:
            mod_ids = SECTION_TOOL_NUMBERS["Network & Infrastructure"]
        elif "Web Intelligence" in sel["name"]:
            mod_ids = SECTION_TOOL_NUMBERS["Web Application Analysis"]
        elif "Security" in sel["name"]:
            mod_ids = SECTION_TOOL_NUMBERS["Security & Threat Intelligence"]
        else:
            mod_ids = []
        if not mod_ids:
            self.pwarning("No modules found for that selection.")
            return
        if not self.target:
            self._prompt_target_if_needed()
        self._invoke_runner(mod_ids, mode_name=sel["name"].upper())
