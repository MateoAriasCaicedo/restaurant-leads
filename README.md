# Restaurant lead pipeline (pilot: Laureles) - free version

Finds restaurants in Medellín and Oriente Antioqueño from OpenStreetMap (no account,
no API key, no Google Cloud), audits their web presence, and ranks them by Sell Score
for web design + digital menu + SEO.

## Setup
```
pip install -r requirements.txt
```

## Web app
```
npm --prefix ui install         # once
npm --prefix ui run build       # once, and again after changing anything in ui/
python app.py                   # http://127.0.0.1:8642 (this machine only)
```
Everything below can be done from the app: the ranked sheet with filters (arrow keys to move, A approve,
X reject, U clear, Enter open), a page per lead (score and reasons, website audit, the neighbours within
500 m drawn as a plot, researched profile, menu, online presence, build plan), a board by status,
a private note and contact log per lead, photo/menu/notes upload, and a Pipeline page that runs
`discover.py` and `audit.py` with a live log. `config.APP_NAME` sets the name in the header; ports are
`UI_PORT` / `UI_DEV_PORT`.

**Get insights** on a lead page researches that one lead with no API key: it runs `enrich.py --collect-only`,
then the Claude Code CLI (`claude -p`) on your subscription, then `ingest.py`. The Claude run is contained:
it works in a throwaway copy of that lead's files under `data/runs/<job>/ws` with no command tools, no MCP
connectors and no access to the rest of the machine; its output is validated against the schemas before
anything is saved, and the previous profile is kept in `data/runs/<job>/prev`. One lead at a time, started by
hand, never in batch. It uses subscription usage and takes several minutes.

Developing the UI: `python app.py --no-browser` plus `npm --prefix ui run dev` (http://localhost:5183,
proxies `/api`). The UI is React + TypeScript + Tailwind + shadcn/ui in `ui/`; the API is `server/`.
`PRODUCT.md` and `DESIGN.md` record what the app is for and how it looks.

## Run from the command line
```
python discover.py laureles     # restaurants from OpenStreetMap -> data/leads.db
python audit.py                 # classify + audit websites (PageSpeed is free); --only PLACE_ID for one place
python score.py                 # writes data/exports/leads_ranked.csv
```
Open `data/exports/leads_ranked.csv` in Sheets/Excel (close it before re-running `score.py`). Tier A first.
The app's CSV button exports the same file without writing it to disk.

### URL health
`audit.py` checks every real website first (`urlcheck.py`): `url_status` in the CSV is `ok`, `dead`
(domain gone / 404), `unreachable` (5xx or timeouts), `parked` (for-sale/placeholder page) or `blocked`
(bot protection: verify by hand). It tries www/http/https/root variants before calling a site dead.
Broken links are scored like "no website" and show "website link is broken" in `why_a_fit`. Just re-run
`python audit.py` periodically: it rechecks non-ok URLs older than `URL_RECHECK_DAYS` (3) on its own, and
`python audit.py --refresh` re-audits everything. PageSpeed is skipped for the rest of a run if the free
API keeps returning 429 (set `GOOGLE_API_KEY` in `.env` to raise the limit).

## Per-lead research (after you pick leads)
```
# put ANTHROPIC_API_KEY in .env (copy .env.example), or set it as an environment variable; needed only for enrich.py
python approve.py approved "la casa" ...      # by name or place_id (column in data/exports/leads_ranked.csv)
#   -> creates data/leads/<slug>/photos/instagram and photos/maps
#   drop Instagram / Google Maps screenshots or photos there (optional: notes.txt with a pasted IG bio/captions)
python enrich.py                              # all approved leads; --only NAME, --refresh, --no-research
#   -> profile saved (read it in the app), status becomes 'enriched'
python approve.py ready "la casa"             # after you review the profile
python approve.py list [status]
```
**No API key? (Claude Max / Claude Code only)** Use the two-step flow instead of `enrich.py`'s LLM steps:
```
python enrich.py --collect-only --only "la casa"   # no key: crawls the site, finds competitors -> data/leads/<slug>/context.md
# in a Claude Code session: ask Claude to analyze that lead; it reads context.md and your photos, researches the web,
# and writes data/leads/<slug>/profile/profile.json (+ optional menu.json, presence.json, design_system.json; formats in schemas.json)
python ingest.py "la casa"                          # validates the profile, records the profile, status -> enriched
```

`enrich.py` (with an API key) crawls the lead's own site (pages, menu PDFs/images, photos, CSS palette and fonts), then uses
Claude to extract the menu, cuisine/tone and photo style, and to write the profile.
It also researches the lead's **working state, reviews and social activity** (`research.py`): Claude's
server-side web search looks for TripAdvisor, Google Maps, Instagram/Facebook, delivery apps and closure
notices, and returns findings with source URLs, an operating-status verdict (active / uncertain / likely
closed / closed), review themes and Instagram activity. Nearby competitors (same cuisine, within 500 m, and
how many have a working site) are computed for free from `data/leads.db`. Web search must be enabled for your
Anthropic organization in the Console and is billed per search on top of tokens; `WEB_SEARCH_MAX_USES` in
`config.py` caps it, and `--no-research` skips it. Search-based numbers are less exact than official APIs:
the profile marks confidence and lists the sources. `data/exports/leads_ranked.csv` gets an `operating_status` column. Results are cached in
`data/leads/<slug>/profile/`, so re-runs only pay for missing stages. Instagram and Maps are never scraped:
photos are dropped in by hand. Models and caps (`MAX_*`) are in `config.py`.

## Add areas
`config.ALL_AREAS` lists every known area; run `python discover.py poblado` (or use the app's Pipeline
page) to survey one. `DEFAULT_AREAS` is what a bare `python discover.py` covers. To add a new area, add
a `name: (lat, lng, radius_m)` entry to `ALL_AREAS`. The query uses a circle (center + radius); raise
the radius or add more centers for larger municipalities.

## Limits of the free data
- OpenStreetMap has no ratings or review counts, so "ability to pay" and "momentum" are
  estimated from how complete the listing is (hours, cuisine, address, services, social
  links). Treat scores as a first filter, then eyeball Tier A/B on Google Maps.
- Coverage in Colombia is patchy: some restaurants are missing. A place with no website
  tag in OSM may actually have one. The audit only checks the URLs OSM knows about, so
  verify "no website" leads with a quick Google search before contacting.
- Fix: you can add restaurants by hand to `data/leads.db` (table `places`) or extend
  `discover.py` with another free source.

## Tuning
Weights, chain and exclusion lists live in `config.py`. Tier cut-offs for OSM data are
`OSM_TIER_A` / `OSM_TIER_B` in `score.py`.

## Notes
- Public business data only. Respect Ley 1581 in outreach (easy opt-out).
- Overpass is a shared free service: run one area at a time and don't hammer it.
