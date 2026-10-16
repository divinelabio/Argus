
from __future__ import annotations

import argparse
from typing import List

from cmd2 import with_argparser, with_category, Cmd2ArgumentParser
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from argus.cli.helpers import resolve_module_number
from argus.core.catalog_cache import TOOL_TAGS, tools_mapping
from argus.core.runner import run_modules

__mixin_name__ = "FavoritesMixin"

console = Console()


class FavoritesMixin:
    _fav_parser = Cmd2ArgumentParser(description="Manage favourites")
    _fav_parser.add_argument("tokens", nargs="*")

    @with_argparser(_fav_parser)
    @with_category("Module Management")
    def do_fav(self, args) -> None: 
        toks: List[str] = args.tokens or ["list"]
        cmd = toks[0]

        match cmd:
            case "list" | "ls":
                self._fav_list()
            case _ if cmd.startswith("tag:"):
                self._fav_from_tag(cmd)
            case "add":
                self._fav_add(" ".join(toks[1:]))
            case "del" | "rm" | "remove":
                self._fav_del(" ".join(toks[1:]))
            case "run":
                self._fav_run_subset([resolve_module_number(t) for t in toks[1:]] if len(toks) > 1 else None)
            case "clear":
                self._fav_clear()
            case "export":
                self._fav_export()
            case "import":
                self._fav_import(" ".join(toks[1:]))
            case _:
                self.perror("fav usage: add|del|run|list|clear|export|import|tag:<tag>")

        self._print_status_bar()

    def _fav_add(self, ident: str) -> None:
        mod = self._resolve_by_any(ident)
        if not mod:
            self.perror("Module not found.")
            return
        self.favorite_modules.add(mod["number"])
        self.poutput(f"Added [bold]{mod['name']}[/bold] to favorites.")

    def _fav_del(self, ident: str) -> None:
        mod = self._resolve_by_any(ident)
        if not mod:
            self.perror("Module not found.")
            return
        try:
            self.favorite_modules.remove(mod["number"])
            self.poutput(f"Removed [bold]{mod['name']}[/bold] from favorites.")
        except KeyError:
            self.pwarning("That module was not in favorites.")

    def _fav_from_tag(self, token: str) -> None:
        tag = token.split(":", 1)[1]
        added = 0
        for mid, tags in TOOL_TAGS.items():
            if tag in tags:
                self.favorite_modules.add(mid)
                added += 1
        self.poutput(f"{added} modules with tag '{tag}' added to favorites.")

    def _fav_clear(self) -> None:
        count = len(self.favorite_modules)
        self.favorite_modules.clear()
        console.print(f"Cleared {count} favorites.")

    def _fav_export(self) -> None:
        if not self.favorite_modules:
            console.print("No favorites to export.")
            return
        
        fav_list = sorted(self.favorite_modules, key=lambda x: int(x))
        fav_names = [tools_mapping[mid]["name"] for mid in fav_list]
        console.print(f"Favorites ({len(fav_list)}): {', '.join(fav_names)}")

    def _fav_import(self, modules_str: str) -> None:
        if not modules_str.strip():
            console.print("No modules specified for import.")
            return
        
        modules = [m.strip() for m in modules_str.split(",")]
        added = 0
        for module in modules:
            mod = self._resolve_by_any(module)
            if mod:
                self.favorite_modules.add(mod["number"])
                added += 1
            else:
                console.print(f"Module '{module}' not found, skipping.")
        
        console.print(f"Imported {added} modules to favorites.")

    def _fav_list(self) -> None:
        if not self.favorite_modules:
            self.pwarning("Favorites list empty.")
            return
        tbl = Table(title="Favorites", box=None, expand=False)
        tbl.add_column("ID", style="yellow", no_wrap=True)
        tbl.add_column("Name", style="green")
        tbl.add_column("Tags", style="magenta")

        for mid in sorted(self.favorite_modules, key=lambda x: int(x)):
            t = tools_mapping[mid]
            tags = " ".join(f"[{tg}]" for tg in sorted(TOOL_TAGS[mid]))
            tbl.add_row(mid, t["name"], tags)
        console.print(tbl)

    def _fav_run(self) -> None:
        if not self.favorite_modules:
            self.pwarning("Favorites list empty.")
            return
        self._run_ids(sorted(self.favorite_modules, key=lambda x: int(x)), "FAVORITES")

    def _fav_run_subset(self, subset: List[str] | None) -> None:
        if subset:
            subset = [x for x in subset if x]
            if not subset:
                self.perror("No valid IDs supplied.")
                return
            self._run_ids(subset, "FAV_SUBSET")
        else:
            self._fav_run()

    def _run_ids(self, ids: List[str], mode: str) -> None:
        if not self.target:
            self._prompt_target_if_needed()
        console.print(Panel(f"Running: {', '.join(ids)}", border_style="blue"))
        run_modules(ids, self.api_status, self.target, self.threads, mode, self)
