"""
High-level execution helpers:
    profile
"""

import argparse
from typing import List

from cmd2 import with_argparser, with_category, Cmd2ArgumentParser
from rich.console import Console

from argus.core.runner import run_modules
from argus.cli.helpers import PROFILE_DEFAULTS

__mixin_name__ = "FlowControlMixin"


class FlowControlMixin:
    _prof_parser = Cmd2ArgumentParser(description="Apply option profile")
    _prof_parser.add_argument("name", choices=list(PROFILE_DEFAULTS))

    @with_argparser(_prof_parser)
    @with_category("Configuration")
    def do_profile(self, args) -> None:
        prof = PROFILE_DEFAULTS[args.name]
        self.global_option_overrides["max_pages"] = str(prof["max_pages"])
        self.global_option_overrides["warn_ms"] = str(prof["warn_ms"])
        self.global_option_overrides["full_chain"] = str(int(prof["full_chain"]))
        self.threads = max(self.threads, int(prof["threads_min"]))
        Console().print(f"[bold green]Profile '{args.name}' applied.[/bold green]")
