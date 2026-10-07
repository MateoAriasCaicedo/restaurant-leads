"""Helpers shared by the Markdown exports (build plan, design system).

Everything in a profile was written by a model reading public web content, so every field is read defensively:
values of the wrong type are dropped, never raised on, and text cannot open a heading, quote, table row or code
fence of its own.
"""
import re
from datetime import datetime

CLOSED = {"closed": "closed", "likely_closed": "likely closed", "uncertain": "not confirmed as open"}


def obj(v):
    return v if isinstance(v, dict) else {}


def as_list(v):
    return v if isinstance(v, list) else []


_BLOCK_START = re.compile(r"#{1,6}(\s|$)|[>|`~]")


def escape(line):
    """Stop text from opening a heading, quote, table row or code fence of its own. A hex colour like
    #2b2a29 is not a heading, and palette entries start with one."""
    return "\\" + line if _BLOCK_START.match(line) else line


def one(v):
    """A value as one line of text, so it can sit inside a list item."""
    return escape(" ".join(v.split())) if isinstance(v, str) else ""


def para(v):
    """Prose as paragraphs (blank-line separated), each collapsed to one line."""
    if not isinstance(v, str):
        return ""
    return "\n\n".join(one(p) for p in re.split(r"\n\s*\n", v) if p.strip())


def lines(v):
    return [t for t in map(one, as_list(v)) if t]


def bullets(items, ordered=False):
    return "\n".join(f"{f'{i}.' if ordered else '-'} {t}" for i, t in enumerate(lines(items), 1))


def facts(rows):
    return "\n".join(f"- **{k}:** {v}" for k, v in rows if v)


def section(title, *blocks, level=2):
    """A heading and its blocks, or nothing at all when every block is empty."""
    body = "\n\n".join(b for b in blocks if b)
    return f"{'#' * level} {title}\n\n{body}" if body else ""


def sub(title, *blocks, level=3):
    return section(title, *blocks, level=level)


def stamp(v):
    try:
        return datetime.fromtimestamp(v).date().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def status_warning(profile):
    op = obj(obj(profile).get("operating_status"))
    verdict = op.get("verdict")
    if not isinstance(verdict, str) or verdict not in CLOSED:
        return ""
    why = one(op.get("reasoning"))
    return f"> **Check before building:** the research rates this restaurant as {CLOSED[verdict]}." + (f" {why}" if why else "")
