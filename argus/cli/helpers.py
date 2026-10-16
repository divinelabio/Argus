import difflib, re, random, time
from typing import List, Dict, Set
from rich.prompt import Prompt, Confirm
from rich.console import Console
from rich.panel import Panel
from argus.core.catalog_cache import (
    tools,
    tools_mapping,
    TOOL_TAGS,
    ALL_KNOWN_MODULE_OPTIONS,
    NUMERIC_OPTION_HINTS,
    resolve_module_number,
)
from argus.core.runner import run_modules
from argus.utils.util import check_api_configured, clean_domain_input

console = Console()

def fuzzy_find_modules(keyword: str):
    k = keyword.lower()
    exact = [t for t in tools if k == t["number"] or k == t["name"].lower()]
    if exact:
        return exact
    part = [t for t in tools if k in t["name"].lower() or k in t.get("description", "").lower()]
    if part:
        return part
    names = [t["name"] for t in tools]
    close = difflib.get_close_matches(keyword, names, n=10, cutoff=0.5)
    return [t for t in tools if t["name"] in close]

def regex_find_modules(pattern: str):
    try:
        rx = re.compile(pattern, re.I)
    except re.error:
        return []
    return [t for t in tools if rx.search(t["name"]) or rx.search(t.get("description", ""))]

def infer_numeric(v: str):
    if v.isdigit():
        return True
    try:
        float(v)
        return True
    except Exception:
        return False

def numeric_or_warn(key: str, value: str):
    if key not in NUMERIC_OPTION_HINTS:
        return True
    return infer_numeric(value)

def suggest_option_name(bad: str, allowed: List[str]):
    m = difflib.get_close_matches(bad, allowed, n=1, cutoff=0.6)
    return m[0] if m else None

def _find_first_by_name_fragment(fragment: str):
    f = fragment.lower()
    for t in tools:
        if f in t["name"].lower():
            return t
    m = fuzzy_find_modules(f)
    return m[0] if m else None

PROFILE_DEFAULTS = {
    "speed": {"max_pages": 25, "warn_ms": 800, "full_chain": False, "threads_min": 8},
    "deep": {"max_pages": 200, "warn_ms": 2000, "full_chain": True, "threads_min": 4},
    "safe": {"max_pages": 10, "warn_ms": 200, "full_chain": False, "threads_min": 2},
}
