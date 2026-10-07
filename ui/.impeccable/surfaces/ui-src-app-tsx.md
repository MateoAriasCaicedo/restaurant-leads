---
version: 1
slug: "ui-src-app-tsx"
primary_target: "ui/src/App.tsx"
related_targets: []
---

# Surface brief: the Daan Agency leads app

Scope: the whole app shell and its four views (leads sheet, lead page, board, pipeline). Visitor mode: Operate.

Audience and job: one designer-developer at a desk in daylight, scanning a neighbourhood's restaurants to end the sitting with a short list worth approving and researching. Primary task: read rank, reason and reachability per row; approve or reject; open one lead to study it. Proof on hand: 235 real places in Laureles, two researched leads. Constraints: desktop-first, English UI with Spanish names, local only, most leads have no profile and no website, all analysis text is untrusted.

Unresolved: none blocking. Map view and phone access are out of scope for this version.

## Direction contract

THESIS: Every lead is a plot on the neighbourhood's survey sheet: numbered, zoned by tier, lettered like a plan. It refuses the white CRM table with one accent and KPI cards on top.

OWN-WORLD: Cool vellum sheet (#EEF0EA), ink (#15201D) linework and a dark ink rail. Zoning fills carry meaning: red is tier A, yellow tier B, unzoned hatch tier C; blue alone owns live state (selection, focus, running jobs); green means verified or working. Square corners, 1px ruled lines, condensed plan lettering in caps for labels and codes, tabular figures.

STORY: The user sees who ranks first and why, trusts the reason because it sits beside the score, and approves, rejects or opens the plot.

FIRST VIEWPORT: Ink rail at left (Leads, Board, Pipeline, jobs at the foot). Filters across the top of the sheet. The ranked table fills the centre: plot number, tier zone, score with its parcel strip (lots of 30/30/20/20 for need, ability, momentum, reach, filled to the amount earned), name with its reasons beneath, web state, reach, status. Top right, a title block with area, counts and survey date; under it the selected plot's panel with reasons, contact details and the approve / reject / open actions. On a lead page the 500 m block is drawn as a plot of the real neighbours.

FORM: The municipal survey plan, position 7 of 7 on the ordered list; seed key 92168728. Code-led: no image generation in this session. Raises: every lead carries one stable plot number (from the catalog sleeve); rejected and excluded leads are struck in place, never removed (from the ticket wallet); one colour owns every live state (from the typographic tiles).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
