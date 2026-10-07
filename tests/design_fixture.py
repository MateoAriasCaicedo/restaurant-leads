"""A complete, valid design_system.json shared by the design system tests."""

DS = {
    "concept": "A warm grill house: charcoal, paper and chili red.",
    "principles": ["Photos first", "One accent per screen"],
    "colors": [
        {"name": "paper", "hex": "#faf5ec", "role": "background", "usage": "Page background"},
        {"name": "card", "hex": "#fffdf8", "role": "surface", "usage": "Menu cards"},
        {"name": "charcoal", "hex": "#2B2A29", "role": "ink", "usage": "Text | headings"},
        {"name": "ash", "hex": "#5a5651", "role": "muted", "usage": "Secondary text"},
        {"name": "chili", "hex": "#b3321f", "role": "accent", "usage": "Buttons and links"},
        {"name": "cream", "hex": "#ffffff", "role": "accent-ink", "usage": "Label on chili"},
    ],
    "fonts": [
        {"role": "heading", "family": "Playfair Display", "kind": "serif", "weights": [700, 600], "why": "Matches the menu card"},
        {"role": "body", "family": "Lato", "kind": "sans", "weights": [400, 700]},
    ],
    "type_scale": [
        {"token": "h1", "size": "clamp(1.75rem, 5vw, 2.5rem)", "line_height": "1.15", "weight": 700, "usage": "Page titles"},
        {"token": "body", "size": "1rem", "line_height": "1.5", "weight": 400},
        {"token": "price", "size": "1.125rem", "weight": 700},
    ],
    "spacing": {"scale": ["4px", "8px", "16px", "24px"], "max_width": "72rem", "layout": "One column on phones."},
    "shape": {"radius": "6px", "borders": "1px lines", "shadows": "None"},
    "imagery": {"treatment": "Warm crops", "aspect_ratios": ["4:3", "1:1"], "guidelines": ["No stock photos"]},
    "components": [{"name": "Dish row", "description": "Name left, price right.",
                    "classes": [{"part": "row", "classes": "flex items-baseline justify-between gap-4 border-b border-ash py-3"},
                                {"part": "price", "classes": "text-price text-chili tabular-nums"}],
                    "states": ["sold out"], "used_on": ["Menu", "Home"]}],
    "motion": "Fade only.",
    "accessibility": ["Visible focus ring"],
    "microcopy": [{"context": "Reserve button", "text": "Reservar mesa"}],
    "dos": ["Use chili once per screen"],
    "donts": ["No gradients"],
    "basis": "Four Instagram screenshots; no logo file, so colours are estimated.",
}
