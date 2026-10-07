"""Every restaurant site is built with config.SITE_STACK. The analysis is told so, but a plan written before that
rule (or by a model that ignored it) can still name Astro, plain HTML and the like. apply() makes the plan's
tech_stack say what the studio builds with, when a lead is read; the files and the database are not touched, so
nothing is lost and a newer analysis simply agrees from the start.
"""
import re

from leadgen import config

# Layers whose choice the fixed stack already makes: the framework and how it is styled.
DECIDED = re.compile(r"framework|front[- ]?end|styl|css", re.I)
WHY = "Fixed: every site is built with it."


def apply(profile):
    """The profile with its plan's tech_stack set to the fixed stack first, then every row about anything else
    (menu data, hosting, images, analytics...). Returns the profile itself when it has no plan; never mutates."""
    dev = profile.get("development_direction") if isinstance(profile, dict) else None
    if not isinstance(dev, dict) or not dev:
        return profile
    rows = dev.get("tech_stack") if isinstance(dev.get("tech_stack"), list) else []
    kept = [r for r in rows if not (isinstance(r, dict) and isinstance(r.get("layer"), str) and DECIDED.search(r["layer"]))]
    fixed = [{"layer": layer, "choice": choice, "why": WHY} for layer, choice in config.SITE_STACK]
    return profile | {"development_direction": dev | {"tech_stack": fixed + kept}}
