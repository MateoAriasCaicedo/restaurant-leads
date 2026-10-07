"""Claude calls for the enrichment pipeline. Every call forces a tool so output is structured JSON."""
import base64
import io
import json
import os
from pathlib import Path

from leadgen import config

_client = None

STR = {"type": "string"}
STRS = {"type": "array", "items": STR}

MENU_SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {"type": "array", "items": {"type": "object", "properties": {
            "name": STR,
            "items": {"type": "array", "items": {"type": "object", "properties": {
                "name": STR, "description": STR, "price_cop": {"type": ["number", "null"]},
            }, "required": ["name"]}},
        }, "required": ["name", "items"]}},
        "notes": {"type": "string", "description": "Anything odd: unreadable parts, combos, daily menu, etc."},
    },
    "required": ["sections"],
}

FACTS_SCHEMA = {
    "type": "object",
    "properties": {
        "cuisine": STRS, "specialties": STRS,
        "price_signals": {"type": "string"},
        "tone_of_voice": {"type": "string", "description": "e.g. warm/familiar, formal, playful; Spanish register, emoji use"},
        "hours": STR, "delivery_or_reservation": STR, "audience": STR, "history_or_story": STR,
    },
    "required": ["cuisine", "specialties", "tone_of_voice"],
}

PHOTO_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_vibe": STR, "setting": {"type": "string", "description": "interior / terrace / street / kitchen, decor style"},
        "lighting": STR, "color_mood": STRS, "photography_style": STR,
        "plating_and_food": {"type": "string", "description": "what the food looks like, signature dishes visible"},
        "audience_signals": STR, "photo_quality": {"type": "string", "enum": ["low", "medium", "high"]},
        "design_direction_hint": {"type": "string", "description": "what a website for this place should feel like"},
    },
    "required": ["overall_vibe", "color_mood", "photo_quality", "design_direction_hint"],
}

PRESENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "platforms": {"type": "array", "items": {"type": "object", "properties": {
            "platform": {"type": "string", "description": "Google Maps, TripAdvisor, Instagram, Facebook, Rappi, iFood, Domicilios, Foursquare, Yelp, other"},
            "found": {"type": "boolean"}, "url": STR, "handle": STR,
            "rating": {"type": ["number", "null"]}, "review_count": {"type": ["integer", "null"]},
            "followers": {"type": ["integer", "null"]},
            "last_activity": {"type": "string", "description": "date or phrase like 'last post March 2026'; empty if unknown"},
            "notes": STR}, "required": ["platform", "found"]}},
        "review_themes": {"type": "object", "properties": {
            "praise": STRS, "complaints": STRS, "sample_quotes": STRS,
            "recent_review_activity": {"type": "string", "description": "how recent and frequent the newest reviews are"}}},
        "instagram": {"type": "object", "properties": {
            "handle": STR, "followers": {"type": ["integer", "null"]}, "posting_frequency": STR,
            "last_post": STR, "content_style": STR}},
        "operating_signals": {"type": "array", "items": {"type": "object", "properties": {
            "signal": STR, "direction": {"type": "string", "enum": ["open", "closed", "unclear"]},
            "evidence": STR, "source_url": STR, "date": STR}, "required": ["signal", "direction", "evidence"]}},
        "verdict": {"type": "object", "properties": {
            "status": {"type": "string", "enum": ["active", "uncertain", "likely_closed", "closed"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]}, "reasoning": STR},
            "required": ["status", "confidence", "reasoning"]},
        "recognition": STRS, "promotions_or_events": STRS,
        "identity_check": {"type": "string", "description": "how you confirmed these results are this exact restaurant"},
        "caveats": STRS,
    },
    "required": ["platforms", "operating_signals", "verdict", "identity_check"],
}

DEV_SCHEMA = {
    "type": "object",
    "description": "How to build the lead's website/digital menu and how to win the lead; written for the developer.",
    "properties": {
        "summary": {"type": "string", "description": "Recommended approach in 3-4 sentences"},
        "deliverables": STRS,
        "goals": STRS,
        "pages": {"type": "array", "items": {"type": "object", "properties": {
            "name": STR, "purpose": STR, "key_content": STRS}, "required": ["name", "purpose"]}},
        "features": {"type": "array", "items": {"type": "object", "properties": {
            "name": STR, "detail": STR, "priority": {"type": "string", "enum": ["must", "should", "later"]}},
            "required": ["name", "priority"]}},
        "menu_system": {"type": "string", "description": "How the digital menu is modelled, rendered and updated"},
        "tech_stack": {"type": "array", "description": f"Only the choices around the fixed stack ({config.SITE_STACK_TEXT}), never an alternative to it",
                       "items": {"type": "object", "properties": {
                           "layer": STR, "choice": STR, "why": STR}, "required": ["layer", "choice"]}},
        "seo_plan": {"type": "object", "properties": {
            "target_keywords": STRS, "on_page": STRS, "local": STRS, "structured_data": STRS}},
        "integrations": STRS,
        "content_needed": STRS,
        "domain_and_hosting": STR,
        "phases": {"type": "array", "items": {"type": "object", "properties": {
            "name": STR, "size": {"type": "string", "enum": ["S", "M", "L"]}, "tasks": STRS},
            "required": ["name", "tasks"]}},
        "risks": STRS,
        "outreach": {"type": "object", "description": "How to approach and win this lead", "properties": {
            "channels": STRS, "timing": STR, "talking_points": STRS,
            "objections": {"type": "array", "items": {"type": "object", "properties": {
                "objection": STR, "response": STR}, "required": ["objection", "response"]}},
            "compliance": STR}},
        "next_steps": STRS,
    },
    "required": ["summary", "deliverables", "pages", "features", "phases", "next_steps"],
}

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "identity": {"type": "object", "properties": {
            "cuisine": STRS, "specialties": STRS,
            "price_tier": {"type": "string", "enum": ["budget", "mid", "upscale", "unknown"]},
            "audience": STR, "positioning": STR}, "required": ["cuisine", "price_tier", "positioning"]},
        "visual_identity": {"type": "object", "properties": {
            "vibe": STR, "palette": STRS, "typography": STR, "photo_style": STR}, "required": ["vibe"]},
        "tone_of_voice": STR,
        "menu_summary": STR,
        "operating_status": {"type": "object", "properties": {
            "verdict": {"type": "string", "enum": ["active", "uncertain", "likely_closed", "closed", "unknown"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]}, "reasoning": STR},
            "required": ["verdict", "reasoning"]},
        "reputation": {"type": "object", "properties": {
            "summary": STR, "ratings_overview": STR, "praise": STRS, "complaints": STRS}},
        "online_activity": STR,
        "competitive_landscape": STR,
        "web_gaps": STRS,
        "design_direction": {"type": "object", "properties": {
            "site_structure": STRS, "menu_experience": STR,
            "palette_suggestion": STR, "typography_suggestion": STR}, "required": ["site_structure", "menu_experience"]},
        "development_direction": DEV_SCHEMA,
        "pitch_hooks": {"type": "array", "items": STR, "description": "Exactly 3 specific, personalized openers"},
        "confidence": {"type": "array", "items": {"type": "object", "properties": {
            "field": STR, "level": {"type": "string", "enum": ["high", "medium", "low"]},
            "source": STR, "note": STR}, "required": ["field", "level", "source"]}},
    },
    "required": ["identity", "visual_identity", "tone_of_voice", "operating_status", "web_gaps", "design_direction", "pitch_hooks", "confidence"],
}

# Formats the design system must keep to. The site is built with Next.js and Tailwind CSS v4, and
# server/designsystem.py turns these values into its theme CSS, next/font code and class lists, so it enforces the
# same patterns again when it reads them back.
HEX_RE = r"^#[0-9a-fA-F]{6}$"
LENGTH_RE = r"^(0|\d{1,3}(\.\d{1,4})?(rem|em|px))$"
SIZE_RE = r"^(0|\d{1,3}(\.\d{1,4})?(rem|em|px)|clamp\([0-9a-z.,% +-]{3,60}\))$"
LEADING_RE = r"^(\d{1,2}(\.\d{1,4})?|\d{1,3}(\.\d{1,4})?(rem|em|px))$"
TOKEN_RE = r"^[a-z][a-z0-9-]{0,29}$"                     # becomes part of a utility: bg-<token>, text-<token>
FONT_RE = r"^[A-Za-z][A-Za-z0-9 ]{0,39}$"                # a next/font/google export once the spaces become underscores
RATIO_RE = r"^(\d{1,2}):(\d{1,2})$"                      # becomes aspect-[W/H]
CLASSES_RE = r"^(?!.*url\()(?!.*//)[A-Za-z0-9 :/\[\]_.%!@*=,()-]{1,400}$"     # utility classes: no #hex values, quotes, urls or markup
COLOR_ROLES = ["background", "surface", "ink", "muted", "border", "accent", "accent-ink", "highlight", "success", "danger"]
FONT_KINDS = ["serif", "sans", "display", "script", "mono"]


def _fmt(pattern, description):
    return {"type": "string", "pattern": pattern, "description": description}


DESIGN_SYSTEM_SCHEMA = {
    "type": "object",
    "description": "The visual system for this restaurant's website and digital menu, written for the agent that builds it with Next.js (App Router) "
                   "and Tailwind CSS v4. development_direction says what to build; this says how it looks and sounds. Ground it in this "
                   "restaurant's real identity (signage, menu card, dishes, interior, photos), not in a generic restaurant template. "
                   "Everything is expressed as Tailwind theme tokens and utility classes: no arbitrary values, no inline styles.",
    "properties": {
        "concept": {"type": "string", "description": "The design idea in 2-3 sentences: the feeling, and the real things about this restaurant it comes from"},
        "principles": {"type": "array", "items": STR, "description": "3-6 short rules that settle design arguments on this site"},
        "colors": {"type": "array", "description": "5-9 tokens. They replace Tailwind's default palette, so every colour the site uses must be here. Use exact hex values "
                                                   "read from the logo, signage, menu card or photos where you can see them. Include at least the roles "
                                                   "background, ink, accent and accent-ink: the export computes their contrast.",
                   "items": {"type": "object", "properties": {
                       "name": _fmt(TOKEN_RE, "Lowercase word that says the job, e.g. paper, charcoal, chili. It becomes the utilities bg-<name>, "
                                              "text-<name>, border-<name>. No numbers; avoid Tailwind's own names (white, black, gray)"),
                       "hex": _fmt(HEX_RE, "Six-digit hex such as #2b2a29"),
                       "role": {"type": "string", "enum": COLOR_ROLES},
                       "usage": {"type": "string", "description": "Where it is used and where it must not be"}},
                       "required": ["name", "hex", "role"]}},
        "fonts": {"type": "array", "description": "Free Google Fonts families that next/font/google can load: one for headings, one for body, optionally one accent",
                  "items": {"type": "object", "properties": {
                      "role": {"type": "string", "enum": ["heading", "body", "accent"], "description": "Becomes the utility font-<role>"},
                      "family": _fmt(FONT_RE, "Exact Google Fonts family name with spaces, e.g. Playfair Display or Source Sans 3"),
                      "kind": {"type": "string", "enum": FONT_KINDS},
                      "weights": {"type": "array", "items": {"type": "integer"}},
                      "why": STR}, "required": ["role", "family", "kind"]}},
        "type_scale": {"type": "array", "description": "Mobile-first. Tokens such as display, h1, h2, h3, body, small, price. Headings may use clamp()",
                       "items": {"type": "object", "properties": {
                           "token": _fmt(TOKEN_RE, "Becomes the utility text-<token>, e.g. h1. Avoid Tailwind's own sizes (xs, sm, base, lg, xl)"),
                           "size": _fmt(SIZE_RE, "rem, em or px, e.g. 1.125rem, or clamp(1.75rem, 5vw, 2.5rem)"),
                           "line_height": _fmt(LEADING_RE, "Unitless (1.4) or a length (1.5rem)"),
                           "weight": {"type": "integer"}, "usage": STR}, "required": ["token", "size"]}},
        "spacing": {"type": "object", "properties": {
            "scale": {"type": "array", "items": _fmt(LENGTH_RE, "e.g. 8px"),
                      "description": "The steps the site uses, as multiples of 4px: they map to Tailwind's spacing units (4px = 1, as in p-1). E.g. 4px 8px 12px 16px 24px 32px 48px 72px"},
            "max_width": _fmt(LENGTH_RE, "Content width, e.g. 72rem. Becomes the utility max-w-site"),
            "layout": {"type": "string", "description": "Grid, section rhythm and how the layout changes on a phone, using Tailwind's breakpoints (sm 40rem, md 48rem, lg 64rem, xl 80rem)"}}},
        "shape": {"type": "object", "properties": {
            "radius": _fmt(LENGTH_RE, "Corner radius for buttons and cards, e.g. 6px. Becomes the utility rounded-brand"),
            "borders": STR, "shadows": STR}},
        "imagery": {"type": "object", "properties": {
            "treatment": {"type": "string", "description": "How photos are cropped, toned and framed so they look like this restaurant"},
            "aspect_ratios": {"type": "array", "items": _fmt(RATIO_RE, "Width:height, e.g. 4:3. Becomes aspect-[4/3] around a next/image"), "description": "Only the ratios the site uses"},
            "guidelines": STRS}},
        "components": {"type": "array", "description": "The pieces the site is assembled from. Cover the digital menu in detail: category navigation, dish row "
                                                       "(name, description, price, dietary tags), the call to action, hours and location, footer",
                       "items": {"type": "object", "properties": {
                           "name": STR, "description": {"type": "string", "description": "What it looks like and how it behaves, in terms of the tokens"},
                           "classes": {"type": "array", "description": "The Tailwind classes of the component's main elements, mobile first. Use only your own tokens "
                                                                       "(bg-charcoal, text-price, rounded-brand, max-w-site), Tailwind's spacing units and the sm:/md:/lg: "
                                                                       "prefixes, focus-visible: and motion-safe:. No arbitrary colours such as bg-[#fff]",
                                       "items": {"type": "object", "properties": {
                                           "part": {"type": "string", "description": "Which element, e.g. row, name, price"},
                                           "classes": _fmt(CLASSES_RE, "Space-separated utility classes")}, "required": ["part", "classes"]}},
                           "states": {"type": "array", "items": STR, "description": "e.g. hover, focus, sold out, selected"},
                           "used_on": {"type": "array", "items": STR, "description": "Names of pages from development_direction.pages"}},
                           "required": ["name", "description"]}},
        "motion": {"type": "string", "description": "What may animate, how long, and that it is wrapped in motion-safe: so reduced-motion is respected"},
        "accessibility": {"type": "array", "items": STR, "description": "Concrete rules: focus ring (focus-visible:), touch target size, text sizes, alt text"},
        "microcopy": {"type": "array", "description": "Example Spanish (es-CO) labels in the restaurant's voice: buttons, hours, menu notes",
                      "items": {"type": "object", "properties": {"context": STR, "text": STR}, "required": ["context", "text"]}},
        "dos": STRS, "donts": STRS,
        "basis": {"type": "string", "description": "What this system rests on (which photos, which files) and how sure it is; say where colours are estimated"},
    },
    "required": ["concept", "colors", "fonts", "type_scale", "components", "basis"],
}


def client():
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY not found. Put it in .env (copy .env.example) or set the environment variable.")
        import anthropic
        _client = anthropic.Anthropic()
    return _client


def image_block(path):
    """Downscale to MAX_IMAGE_PX and re-encode as JPEG (handles webp/png, keeps requests small)."""
    from PIL import Image
    try:
        im = Image.open(path)
        im.load()
    except Exception:
        return None
    im = im.convert("RGB")
    im.thumbnail((config.MAX_IMAGE_PX, config.MAX_IMAGE_PX))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(buf.getvalue()).decode()}}


def pdf_block(path):
    return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                           "data": base64.b64encode(Path(path).read_bytes()).decode()}}


def call(model, system, content, tool, schema, max_tokens=4096):
    resp = client().messages.create(
        model=model, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": content}],
        tools=[{"name": tool, "description": f"Return the {tool.replace('_', ' ')}.", "input_schema": schema}],
        tool_choice={"type": "tool", "name": tool},
    )
    for b in resp.content:
        if b.type == "tool_use":
            return b.input
    raise RuntimeError(f"{tool}: model returned no structured output")


def extract_menu(text, pdfs, images):
    content = [pdf_block(p) for p in pdfs] + [b for b in (image_block(p) for p in images) if b]
    content.append({"type": "text", "text": "Extract this restaurant's menu from the attached files and/or this website text. "
                    "Keep dish names in their original language (usually Spanish). Prices are in Colombian pesos; "
                    "convert '25.000' or '25k' to 25000. If there is no menu, return no sections.\n\nWEBSITE TEXT:\n" + (text or "(none)")})
    return call(config.MODEL_STRONG, "You digitize restaurant menus accurately. Never invent dishes or prices.",
                content, "menu", MENU_SCHEMA, max_tokens=8000)


def site_facts(osm_tags, page_text, notes):
    prompt = (f"OpenStreetMap tags:\n{json.dumps(osm_tags, ensure_ascii=False)}\n\n"
              f"Website text:\n{page_text or '(no website)'}\n\n"
              f"Pasted notes (e.g. Instagram bio/captions):\n{notes or '(none)'}\n\n"
              "Summarize what kind of restaurant this is. Only state what the sources support; leave unknown fields as empty strings.")
    return call(config.MODEL_FAST, "You analyze small restaurants in Colombia for a web-design agency.",
                [{"type": "text", "text": prompt}], "site_facts", FACTS_SCHEMA)


def analyze_photos(source, paths):
    blocks = [b for b in (image_block(p) for p in paths) if b]
    if not blocks:
        return None
    blocks.append({"type": "text", "text": f"These {len(blocks)} images come from the restaurant's {source}. "
                   "Describe the visual identity they project, as a brand designer would. Base it only on what you see."})
    out = call(config.MODEL_STRONG, "You are a brand designer analyzing a restaurant's photography.",
               blocks, "photo_analysis", PHOTO_SCHEMA)
    out["images_analyzed"] = len(blocks) - 1
    return out


def synthesize(payload):
    prompt = ("Everything known about this lead is below as JSON. Produce the lead profile that a designer will use to build "
              "their website and digital menu. Write in English, but keep dish names and any quoted copy in the original Spanish. "
              "Use `online_presence` (web research, may be absent) for operating_status, reputation and online_activity: "
              "never state a rating, follower count or date that is not in it, and use verdict 'unknown' if there was no research. "
              "Use `competitors` for competitive_landscape and for pitch hooks (e.g. neighbors that already have a working site). "
              "If operating_status is likely_closed/closed, say so plainly. "
              "Mark each important field in `confidence` with its source (site, menu, photos:<source>, osm, notes) and rate it "
              "low when it is a guess or rests on few photos. Give exactly 3 pitch hooks that reference concrete things about "
              "this restaurant. Also fill `development_direction` for the developer who will build their website and digital menu: "
              "pages, prioritized features, menu data approach, tech stack, local-SEO plan, content needed from the owner, phased plan "
              "(sizes S/M/L, no prices or day counts), risks, and an outreach plan. The stack is fixed: every site is built with "
              f"{config.SITE_STACK_TEXT}, so do not propose another framework or CSS approach, and list in tech_stack only what is "
              "open around it (menu data, hosting that can run it, images, fonts, analytics). Ground it in the facts above; do not "
              "invent numbers, keywords volumes or legal claims.\n\n" + json.dumps(payload, ensure_ascii=False))
    return call(config.MODEL_STRONG, "You are a senior brand strategist at a web-design agency.",
                [{"type": "text", "text": prompt}], "lead_profile", PROFILE_SCHEMA, max_tokens=12000)


def research_presence(info, today):
    """Server-side web search over public sources. Returns (report_text, sources[])."""
    tool = {"type": config.WEB_SEARCH_TOOL, "name": "web_search", "max_uses": config.WEB_SEARCH_MAX_USES,
            "user_location": {"type": "approximate", "country": "CO", "region": "Antioquia", "city": "Medellín", "timezone": "America/Bogota"}}
    prompt = (f"Today is {today}. Research this restaurant's public online footprint and whether it is currently operating.\n\n{info}\n\n"
              "Find, with the web search tool: its Google Maps listing (status, rating, review count, recent reviews and their dates), "
              "TripAdvisor page (rating, review count, ranking, recent reviews), Instagram and Facebook pages (handle, followers, "
              "how recently and how often it posts), delivery-app listings (Rappi, iFood, Domicilios), Foursquare/Yelp, and any news, "
              "awards, events or notices that it closed or moved. Rules: only report what sources actually show; say 'not found' "
              "otherwise; give the URL and date for every fact; verify it is the same restaurant (name + address + Medellín area) and "
              "ignore same-name places elsewhere. Finish with a plain-text report covering: platforms, review themes (praise and "
              "complaints, with short Spanish quotes), Instagram activity, operating signals (open vs closed evidence), recognition, "
              "and your overall judgment of whether it is active.")
    messages = [{"role": "user", "content": prompt}]
    texts, sources = [], []
    for _ in range(4):                               # server tools may pause a long turn; continue it
        resp = client().messages.create(
            model=config.MODEL_STRONG, max_tokens=8000, tools=[tool], messages=messages,
            system="You are a careful market researcher. Never invent numbers, dates or URLs.")
        for b in resp.content:
            kind = getattr(b, "type", "")
            if kind == "text":
                texts.append(b.text)
            elif kind == "web_search_tool_result" and isinstance(getattr(b, "content", None), list):
                for it in b.content:
                    if getattr(it, "url", None):
                        sources.append({"url": it.url, "title": getattr(it, "title", "") or ""})
        if resp.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": resp.content})
    uniq = list({s["url"]: s for s in sources}.values())
    return "\n".join(texts).strip(), uniq


def extract_presence(report, sources):
    prompt = ("Convert this research report into the structured format. Keep only facts stated in the report; use null/empty "
              "for anything not stated. Choose verdict.status from the evidence: 'active' needs recent signals (reviews, posts, "
              "listings) within roughly the last 3 months; 'uncertain' if evidence is old or thin; 'likely_closed'/'closed' only "
              "if sources say so or all activity stopped long ago.\n\nREPORT:\n" + (report or "(empty)") +
              "\n\nSOURCES SEEN:\n" + "\n".join(f"- {s['url']}" for s in sources[:40]))
    return call(config.MODEL_FAST, "You structure research notes faithfully.",
                [{"type": "text", "text": prompt}], "online_presence", PRESENCE_SCHEMA, max_tokens=4096)
