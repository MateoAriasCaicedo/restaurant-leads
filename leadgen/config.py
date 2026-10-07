"""Configuration for the restaurant lead pipeline."""
import os
from pathlib import Path


def load_env(path=Path(__file__).resolve().parent.parent / ".env"):
    """Load KEY=value lines from .env into os.environ; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text("utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip().strip("'\""):
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


load_env()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")  # optional now: only raises PageSpeed rate limits
# Everything the pipeline writes lives under DATA_DIR (relative to the repo root, which is the working directory).
DATA_DIR = "data"
DB_PATH = f"{DATA_DIR}/leads.db"
EXPORTS_DIR = f"{DATA_DIR}/exports"   # ranked / premium CSVs
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Every area discover.py knows. Each area: (center_lat, center_lng, radius_m).
ALL_AREAS = {
    "laureles": (6.2442, -75.5918, 1800),
    "poblado": (6.2086, -75.5659, 2200),
    "sabaneta": (6.1515, -75.6165, 2000),
    "rionegro": (6.1553, -75.3737, 3000),
    "la_ceja": (6.0329, -75.4300, 2000),
    "el_retiro": (6.0626, -75.5026, 1500),
    "guatape": (6.2338, -75.1597, 1500),
    "marinilla": (6.1739, -75.3361, 1500),
    "guarne": (6.2790, -75.4410, 1500),
    "las_palmas": (6.1542, -75.5350, 1800),   # dense dining cluster on Via Las Palmas (above El Poblado)
    "aeropuerto": (6.1750, -75.4350, 1500),   # roadside restaurants near Jose Maria Cordova airport
}
# Pilot area(s): what `python discover.py` covers with no arguments. Add keys of ALL_AREAS to widen it;
# any other area still works when named explicitly (python discover.py poblado) or from the web app.
DEFAULT_AREAS = ("laureles",)
AREAS = {k: ALL_AREAS[k] for k in DEFAULT_AREAS}

GRID_STEP_M = 700          # distance between search tiles
TILE_RADIUS_M = 500        # search radius per tile
QUERIES = ["restaurante", "restaurant", "comida"]

# Sell Score weights (sum to 100)
WEIGHTS = {"need": 30, "ability": 30, "momentum": 20, "reach": 20}
TIER_A = 80
TIER_B = 60

# Premium lead generation (quality.py): a separate 0-100 quality score for high-end restaurants.
PREMIUM_MIN = 60              # quality score a Maps-verified place needs to be "premium"
PREMIUM_MIN_RATING = 4.4      # ...plus these hard gates
PREMIUM_MIN_REVIEWS = 100
CANDIDATE_MIN = 10            # OSM-only quality that marks a candidate (OSM tags are thin: ~top 5% of a typical area)
PREMIUM_AREA_BONUS = {"poblado": 6, "laureles": 4, "el_retiro": 3, "guatape": 2}

# Price levels we target (Places API: PRICE_LEVEL_INEXPENSIVE..VERY_EXPENSIVE)
TARGET_PRICE_LEVELS = {"PRICE_LEVEL_MODERATE", "PRICE_LEVEL_EXPENSIVE", "PRICE_LEVEL_INEXPENSIVE"}
MIN_REVIEWS = 40

# Domains that are NOT a real website
SOCIAL_DOMAINS = (
    "instagram.com", "facebook.com", "fb.com", "linktr.ee", "linktree.com",
    "wa.me", "whatsapp.com", "tiktok.com", "rappi.com", "ifood.com",
    "tripadvisor.com", "linkin.bio", "beacons.ai", "business.site", "g.page",
)

# Chains / franchises to exclude (lowercase substrings)
CHAINS = (
    "mcdonald", "kfc", "burger king", "subway", "domino", "pizza hut", "papa john",
    "frisby", "crepes & waffles", "crepes y waffles", "el corral", "presto",
    "juan valdez", "starbucks", "wok", "kokoriko", "archies", "sandwich qbano",
    "mimo's", "home burgers", "ocio", "sushi itto", "buffalo wings", "tropical",
)

# Types we skip (hotels, malls, etc.)
EXCLUDED_TYPES = {"lodging", "shopping_mall", "gas_station", "convenience_store", "supermarket"}

REQUEST_DELAY_S = 0.4
USER_AGENT = "Mozilla/5.0 (compatible; LeadAuditBot/1.0)"

# --- Per-lead enrichment pipeline (enrich.py) ---
LEADS_DIR = f"{DATA_DIR}/leads"        # data/leads/<slug>/{photos/instagram,photos/maps,raw,profile}
MODEL_FAST = "claude-haiku-4-5-20251001"   # classification of site text
MODEL_STRONG = "claude-sonnet-5-5"         # menu/photo vision + synthesis
MAX_SITE_PAGES = 6
MAX_PAGE_CHARS = 6000
MAX_SITE_PHOTOS = 8
MAX_PHOTOS_PER_SOURCE = 10   # per drop-in folder (instagram / maps)
MAX_MENU_PDFS = 3
MAX_MENU_IMAGES = 4
MAX_IMAGE_PX = 1568
# Every restaurant site is built with this stack, as (tech_stack layer, choice). The analysis prompts say so and never
# propose another framework; server/sitestack.py makes plans written before this rule agree.
SITE_STACK = (("Framework", "Next.js"), ("Styling", "Tailwind CSS"))
SITE_STACK_TEXT = " and ".join(choice for _, choice in SITE_STACK)

# --- URL health checks (urlcheck.py, run from audit.py) ---
# Broken/blocked URLs are re-checked by `python audit.py` once their last check is this old.
URL_RECHECK_DAYS = 3
# Need is multiplied by this per audit confidence (audits.confidence): "no website" from OSM alone is often a data gap.
CONFIDENCE_NEED_FACTOR = {"high": 1.0, "medium": 0.93, "low": 0.85}
# Website discovery for places OSM lists without one (python audit.py --discover): guessed domains, strictly verified.
DISCOVER_TLDS = ("com", "com.co", "co")
DISCOVER_RETRY_DAYS = 60       # a place whose lookup found nothing is tried again after this long
# A page counts as local when it mentions one of these (compared to the normalised page text).
LOCALITY_WORDS = ("medellin", "antioquia", "envigado", "sabaneta", "rionegro", "laureles", "poblado",
                  "guatape", "la ceja", "el retiro", "marinilla", "guarne", "colombia")
# Sites are fetched like a normal visitor would; a bot-looking UA gets many sites to return 403.
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# --- Reviews / social / working-state research (research.py) ---
WEB_SEARCH_TOOL = "web_search_20250305"   # Anthropic server-side web search tool version
WEB_SEARCH_MAX_USES = 8                   # max searches per lead (main cost control)
COMPETITOR_RADIUS_M = 500

# --- Web app (app.py, server/) ---
APP_NAME = "Daan Agency"      # shown in the app header and browser tab
UI_PORT = 8642
UI_DEV_PORT = 5183            # Vite dev server (npm --prefix ui run dev); allowed as an origin
RUNS_DIR = f"{DATA_DIR}/runs"            # data/runs/<job_id>/{job.json,log.txt,ws/,prev/}: job logs and the headless-Claude workspace
CLAUDE_BIN = "claude"         # Claude Code CLI, run headless on the logged-in subscription (no API key)
CLAUDE_MODEL = "sonnet"
CLAUDE_TIMEOUT_S = 900        # whole analysis run
CLAUDE_IDLE_S = 180           # no output for this long = stuck
CLAUDE_MAX_WEB_CALLS = 30     # WebSearch + WebFetch calls per run
MAX_UPLOAD_MB = 10
