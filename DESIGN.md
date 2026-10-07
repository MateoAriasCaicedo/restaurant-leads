---
name: Daan Agency Leads
description: A neighbourhood's restaurants drawn as a municipal survey plan and ranked as leads.
colors:
  background: "#eef0ea"
  card: "#f7f8f4"
  popover: "#fbfcf9"
  ink: "#15201d"
  muted-foreground: "#51605a"
  muted: "#e4e7e0"
  border: "#c3c9c1"
  input: "#7f8a80"
  faint: "#a9b2a8"
  rail-foreground: "#e3e9e4"
  rail-muted: "#9fb0a8"
  rail-line: "#2e3e38"
  zone-a: "#c63d25"
  zone-b: "#efc62f"
  zone-b-ink: "#2a2200"
  zone-c: "#c2c8bf"
  live: "#2b62a8"
  live-soft: "#dbe5f2"
  accent-foreground: "#14365f"
  good: "#2a7550"
  good-soft: "#dcebe2"
  warn: "#7a5600"
  warn-soft: "#f6e9b8"
  bad: "#b0351f"
  bad-soft: "#f5ddd6"
  white: "#ffffff"
typography:
  display:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: "2rem"
    fontFeature: "\"tnum\" 1"
  headline:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: "2rem"
  title:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: "1.5rem"
  body:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.25rem"
    fontFeature: "\"tnum\" 1"
  body-small:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.43
    fontFeature: "\"tnum\" 1"
  caption:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: "1rem"
    fontFeature: "\"tnum\" 1"
  control:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: "1.25rem"
  label:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    lineHeight: "1rem"
    letterSpacing: "0.07em"
    fontVariation: "'wdth' 72"
  plot-number:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: "1.25rem"
    letterSpacing: "0.02em"
    fontFeature: "\"tnum\" 1"
    fontVariation: "'wdth' 72"
rounded:
  none: "0px"
  sm: "1px"
  md: "2px"
spacing:
  "1": "4px"
  "1.5": "6px"
  "2": "8px"
  "2.5": "10px"
  "3": "12px"
  "4": "16px"
  "6": "24px"
  "8": "32px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.background}"
    typography: "{typography.control}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "32px"
  button-primary-hover:
    backgroundColor: "rgb(21 32 29 / 0.8)"
  button-outline:
    backgroundColor: "{colors.background}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "32px"
  button-outline-hover:
    backgroundColor: "{colors.muted}"
  button-ghost-hover:
    backgroundColor: "{colors.muted}"
    textColor: "{colors.ink}"
  input:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "4px 10px"
    height: "32px"
  rail:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.rail-foreground}"
    width: "208px"
  nav-item:
    textColor: "{colors.rail-foreground}"
    typography: "{typography.control}"
    rounded: "{rounded.none}"
    padding: "6px 10px"
  nav-item-hover:
    backgroundColor: "{colors.rail-line}"
  nav-item-active:
    backgroundColor: "{colors.live}"
    textColor: "{colors.white}"
  tier-zone-a:
    backgroundColor: "{colors.zone-a}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    size: "20px"
  tier-zone-b:
    backgroundColor: "{colors.zone-b}"
    textColor: "{colors.zone-b-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    size: "20px"
  tier-zone-c:
    backgroundColor: "{colors.background}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    size: "20px"
  status-stamp:
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 6px"
    height: "20px"
  status-stamp-enriched:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.background}"
  status-stamp-ready:
    backgroundColor: "{colors.good}"
    textColor: "{colors.white}"
  status-stamp-contacted:
    textColor: "{colors.good}"
  status-stamp-rejected:
    textColor: "{colors.muted-foreground}"
  mark-live:
    backgroundColor: "{colors.live-soft}"
    textColor: "{colors.accent-foreground}"
    typography: "{typography.label}"
    padding: "0 6px"
    height: "20px"
  mark-good:
    backgroundColor: "{colors.good-soft}"
    textColor: "{colors.good}"
    typography: "{typography.label}"
    padding: "0 6px"
    height: "20px"
  mark-warn:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
    typography: "{typography.label}"
    padding: "0 6px"
    height: "20px"
  mark-bad:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.bad}"
    typography: "{typography.label}"
    padding: "0 6px"
    height: "20px"
  sheet-row-selected:
    backgroundColor: "{colors.live-soft}"
  title-block-cell:
    backgroundColor: "{colors.background}"
    typography: "{typography.body-small}"
    padding: "6px 12px"
  board-card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.none}"
    padding: "10px"
  tooltip:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.background}"
    typography: "{typography.caption}"
    rounded: "{rounded.md}"
    padding: "6px 12px"
---

# Design System: Daan Agency Leads

## Overview

**Creative North Star: "The Plano Catastral"**

Every restaurant is a plot on the neighbourhood's survey sheet: numbered, zoned by tier, lettered like a municipal plan. The app is a working drawing, not a dashboard. A cool drafting-film sheet carries ink linework, a dark ink rail runs down the left edge like the binding strip of a plan set, and the few saturated colours are zoning fills that mean exactly one thing each. The person reading it is one designer at a desk in daylight, deciding who to pitch next; the sheet has to be dense, quiet and exact enough to scan 200 rows and still trust each one.

Density is Operate density. Body text is 14 px, rows carry a name and the reason it ranks beneath it, figures are tabular everywhere, and labels are set in condensed plan lettering so a column head or a stamp takes little width. Structure comes from 1 px ruled lines rather than boxes, fills or shadows: ink rules for the plan's own divisions, a quieter survey-line grey for row separators. Corners are square. Nothing floats except shadcn overlays.

The world explicitly refuses the white CRM table with one accent colour and KPI cards stacked on top. Counts live in a ruled title block, the way a plan carries its area, date and sheet totals in the corner.

**Key Characteristics:**
- Drafting-film sheet, ink linework, an ink rail; flat, ruled, square-cornered.
- Zoning colour (red, yellow, hatched grey) belongs to tiers A, B and C and to nothing else.
- One live colour: Survey Blue marks selection, focus, the active rail item, running work and drop targets.
- What stands on a plot is drawn as an ink glyph whose shape carries the state; the only filled glyph is a verified working site, in green.
- Condensed uppercase plan lettering for labels, codes, column heads and stamps; tabular figures throughout.
- Every lead keeps one stable plot number, and rejected or excluded leads are struck in place rather than removed.

## Colors

A restrained film-and-ink palette with three zoning fills, one live blue and a muted set of state plates; every saturated colour has one job.

### Primary
- **Plan Ink** (#15201d): a deep green-black used for all text, every drawn rule (`--rule`), the borders of tier zones and parcel strips, the primary button fill, the enriched stamp, tooltips, and the rail (`--rail`, kept as its own token but equal to ink). shadcn's `foreground`, `primary`, `card-foreground` and `popover-foreground` all resolve to it.

### Secondary
- **Survey Blue** (#2b62a8): the single live-state colour. Selection, keyboard focus (2 px outline, or a 3 px ring at 50% on shadcn controls), the active rail item, running jobs and steps, the research-in-progress frame, drag-over drop zones, text selection and the caret. shadcn's `ring` resolves to it.
- **Survey Blue Wash** (#dbe5f2): the soft fill of a live state: the selected sheet row, a pressed tier filter, a drop target, the running job mark. shadcn's `accent` resolves to it.
- **Deep Survey Blue** (#14365f): text on the blue wash, so live marks stay legible (9.6:1).

### Tertiary
The zoning. These are the plan's land-use fills and they mark tier only.
- **Zone A Vermilion** (#c63d25): tier A. Fills the tier zone (white letter), the parcel strip lots of a tier-A lead, and the lead's own plot in the block drawing.
- **Zone B Signal Yellow** (#efc62f): tier B, with its letter in **Zone B Ink** (#2a2200).
- **Unzoned Grey** (#c2c8bf): tier C, always drawn as a 135° hatch (1.5 px lines on a 4 px period), never as a flat fill in the tier mark.

### States
- **Verified Green** (#2a7550): verified or working. The one filled web-state glyph (a working site), the ready stamp (white letters on green), the contacted stamp (green outline and letters), audit check marks, the "active" operating verdict. Its plate is **Green Wash** (#dcebe2).
- **Failure Red** (#b0351f): failures and stops. Error alerts, failed jobs, audit X marks, closed or likely-closed verdicts, opt-out warnings, crawl errors. Its plate is **Red Wash** (#f5ddd6). shadcn's `destructive` resolves to it. It is darker and browner than Zone A Vermilion so the two are never confused.
- **Survey Ochre** (#7a5600) on **Straw Plate** (#f6e9b8): caution. Uncertain verdicts, interrupted jobs, the "not audited yet" banner, log warnings. Ochre and straw are deliberately far from Signal Yellow.

### Neutral
- **Drafting Film** (#eef0ea): the sheet. Page background, table header, the plate behind the tier C letter, outline-button fill.
- **Clean Film** (#f7f8f4): one step lighter, for figures and contained material: the block drawing, the job log, board cards, the in-row plot panel, alerts, analysis chips.
- **Overlay Film** (#fbfcf9): popovers, select lists, menus and the jobs drawer.
- **Pencil** (#51605a): secondary text, reasons under names, lettered labels, asides (5.8:1 on the sheet).
- **Film Shade** (#e4e7e0): hover fills on rows, ghost and outline buttons, the skeleton, the "unknown" verdict plate.
- **Survey Line** (#c3c9c1): the quiet 1 px separator between rows, list items, board columns and around cards and chips.
- **Control Line** (#7f8a80): the stroke of anything you operate: inputs, selects, textareas, checkboxes, outline toggles, keyboard-hint keys, and the dashed frames of drop zones and empty states. It meets the 3:1 non-text floor on the sheet (3.1:1).
- **Survey Grey** (#a9b2a8): absence only. Marks that should read as a gap: missing reach icons, the not-audited glyph (in the sheet and the block drawing), list bullets, pending job-step boxes, the "unknown" audit check, the scrollbar thumb. Never a control stroke.
- **Rail Film** (#e3e9e4), **Rail Pencil** (#9fb0a8), **Rail Line** (#2e3e38): text, secondary text, and dividers or hover fills on the ink rail.
- **White** (#ffffff): letters on Zone A Vermilion, Survey Blue and Verified Green fills, and selected text.

### Named Rules
**The Zoning Rule.** Vermilion, Signal Yellow and the grey hatch are the zoning of tiers A, B and C and are used for nothing else: not for errors, warnings, emphasis or decoration. A failure is Failure Red; a caution is Ochre on Straw.

**The One Live Colour Rule.** Survey Blue means "chosen now" or "happening now". Every live state uses it, and no other hue signals a live state. Nothing decorative is blue.

**The Ink Glyph Rule.** What stands on a plot is drawn in ink and told apart by shape alone, in the sheet and in the block drawing alike. The only filled web glyph is a working site, in Verified Green, because green means verified.

**The Absence Rule.** Survey Grey means something is missing. Anything the user operates is stroked in Control Line, which holds 3:1 on the sheet; the two greys never swap jobs.

## Typography

**Display Font:** Archivo Variable (with ui-sans-serif, system-ui, sans-serif)
**Body Font:** Archivo Variable (same family)
**Label/Mono Font:** Archivo Variable on its width axis, condensed to 72% for plan lettering and plot numbers

**Character:** One self-hosted grotesque used at two widths. At normal width it is a plain, sturdy reading face; condensed and tracked in caps it becomes the lettering of a survey plan. All figures are tabular (`tnum` is set on the body), so scores, counts, plot numbers and distances line up in columns without extra work.

### Hierarchy
- **Display** (600, 1.875rem, 2rem line): the sell score figure on the lead page. The plot panel shows the same figure one step down (1.5rem). Always beside its tier zone and the words "of 100".
- **Headline** (600, 1.5rem, 2rem line): the restaurant's name at the top of the lead page. View titles on Board and Pipeline sit at 1.25rem; the name in the plot panel at 1.125rem.
- **Title** (600, 1rem, 1.5rem line): section headings on a ruled line, board column names, the brand line in the rail. Also the score figure in sheet rows (semibold, tabular, right-aligned).
- **Body** (400, 0.875rem, 1.25rem line): everything else. Restaurant names in rows are semibold body. Long analysis text is held to a 70ch measure.
- **Body small** (400, 0.8125rem): the second register: title-block values, filter facts, legends, links in the plot panel, chips, hints.
- **Caption** (400, 0.75rem): the reason line under each name, section asides, lot explanations, timestamps, the job log.
- **Control** (500, 0.875rem): buttons, rail items, tabs.
- **Label** (600, 0.6875rem, 1rem line, 0.07em tracking, uppercase, 72% width): plan lettering. Column heads, definition-list terms, title-block labels, stamps, marks, tier letters, keyboard keys, drawing annotations.
- **Plot number** (500, 0.75rem, 0.02em tracking, 72% width, tabular): the stable plot code ("N 5546129027": OSM type initial and id), always in Pencil.

### Named Rules
**The Plan Lettering Rule.** Labels, codes, column heads, stamps and tier letters are lettered: condensed, tracked, uppercase, small. Lettering names the value or the group it sits on; it never stands above a heading as a kicker or eyebrow.

**The Tabular Rule.** Every figure is tabular. A number that has to be compared sits right-aligned in its column.

## Layout

The shell is a single ink rail and a sheet. From 768 px the rail is a 208 px column at the left (brand line, Leads, Board, Pipeline, and the Jobs entry at its foot behind a rail-line rule); below 768 px it becomes a top band with the three items in a row and the Jobs entry hidden. The sheet scrolls independently of the rail.

**Leads sheet.** A filter bar runs across the top of the sheet on a 1 px ink rule (search, tier toggles with counts, web-presence and status selects, Has phone, Show excluded, a live "221 plots" count and CSV at the far right), wrapping on narrow widths. The ranked table fills the centre. From 1280 px a 320 px column at the right carries the title block (area, survey date, plots, ranked, researched, tier counts) and, under it, the selected plot's panel. Below 1280 px the title block collapses to a single ruled strip of facts above the table, and the selected plot opens in place under its own row, pinned to the left edge and never wider than 36rem. The plot-number column appears from 768 px and the parcel strip in rows from 640 px.

**Lead page.** Centred, up to 88rem wide, 24 px side gutters. A back link to Leads, then a header ruled in ink underneath: name, web state and verdict, status select and research action at the left; the plot's title block (plot, area, sell score, surveyed) at the right. Below, a two-column grid from 1280 px: tabbed content on the left, a 20rem aside (contact, private note, contact log) on the right, 40 px apart.

**Board and Pipeline.** Board is one column per status, at least 15rem each, scrolling sideways, separated by 1 px survey lines. Pipeline is a single 64rem column of numbered, ruled sections.

**Rhythm.** A 4 px base. Table cells use 8 px padding with a 16 px gutter at the sheet's edges; page gutters are 24 px; lead sections stand 32 px apart; title-block cells are 6 px by 12 px. Sheet rows run about 57 px for two lines of content. Controls are 32 px tall, 28 px in the filter bar, and stamps and tier zones 20 px.

### Named Rules
**The Struck-In-Place Rule.** A rejected lead keeps its row and its rank, struck through; the sheet never silently loses a plot.

**The Title Block Rule.** Totals and reference facts (area, survey date, counts, plot, score) sit in a ruled title block at the corner of the sheet or the lead, never in cards above the table.

## Elevation & Depth

The plan is flat. Depth is drawn, not cast: an ink rule marks a division of the plan (the filter bar, the table header, section titles, the title block, the frames of marks and drawings), a survey-line rule separates items within it (rows, list items, board columns, cards), and a single tonal step separates contained material (Clean Film) from the sheet (Drafting Film). The sticky table header draws its bottom rule with a 1 px inset line so it survives scrolling; that is a ruled line, not elevation. Shadows exist only on shadcn overlays, which genuinely sit above the sheet.

### Shadow Vocabulary
- **Overlay** (`box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` plus a 1 px ink ring at 10%): popovers and select lists.
- **Overlay large** (`box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)`): dropdown menus and the jobs drawer.

### Named Rules
**The Drawn Line Rule.** Every division is a 1 px line: ink for the plan's own structure, survey line for separation. Surfaces, cards, rows and marks carry no shadow.

## Shapes

Square-cornered, as plans are. The plan's own marks (tier zones, parcel strips, stamps, marks, the title block, board cards, chips, rail items, the block drawing, the research frame) have no radius at all. Interactive controls and overlays (buttons, inputs, selects, popovers, tooltips, alerts, skeletons) take a barely-there 2 px radius (`--radius`, 0.125rem); every larger shadcn radius step collapses to it and the small step is 1 px, so nothing is ever a pill. Lines are 1 px; the only 2 px strokes are the focus outline, the active tab's underline, and in the block drawing the outline of the lead's own plot and the blocked-site bar. Dashes mean vacancy or a boundary: the vacant-plot glyph, the block's distance rings, empty-state and drop-zone frames. Hatching means the unzoned tier C, and, as a faint ink overlay, the large parcel strip.

### Named Rules
**The Square Plan Rule.** The plan's marks have no radius; controls and overlays take 2 px and never more.

## Components

### Buttons
Plain, inked and compact; a button is a label in a ruled box.
- **Shape:** square with a 2 px radius; 32 px tall by default, 28 px small (in filters and section toolbars), 24 px extra-small (inside logs), 36 px large; 10 px side padding, 6 px icon gap, 16 px icons (14 px when small).
- **Primary:** Plan Ink fill, Drafting Film label, Control type. Used for the one decisive action in a place (Approve, Log contact, Audit new and broken).
- **Hover / Focus:** primary hover lightens the ink to 80%; outline and ghost hover take the Film Shade fill. Focus turns the border Survey Blue and adds a 3 px Survey Blue ring at 50%. Pressing nudges the button down 1 px. Disabled is 50% opacity.
- **Outline:** Drafting Film fill, Survey Line border, ink label. The default for secondary actions (Reject, Open, Re-check, CSV).
- **Ghost / Link:** ghost has no fill until hover (Clear filters, Not now, dismiss); link is ink text underlined on hover.

### Chips
- **Status stamps:** 20 px tall, plan lettering, 6 px side padding, square, 1 px border. Approved is an ink outline; enriched is an ink plate with film letters; ready is a Verified Green plate with white letters; contacted is a green outline with green letters; rejected is a survey-line outline with Pencil letters, struck through.
- **Marks:** the same lettering on a soft plate with no border: Green Wash for active or done, Straw for uncertain or interrupted, Red Wash for closed or failed, Survey Blue Wash for running, Film Shade for unknown or waiting. A logged outcome that is neither good nor bad (a conversation under way) takes an ink-outline mark, never the blue wash, because a logged outcome is not live state.
- **Content chips:** cuisine, keywords and similar analysis lists sit in 1 px survey-line boxes on Clean Film, body-small text, 2 px by 6 px padding.
- **Keys:** keyboard hints are lettered keys in a 20 px Control Line box.

### Cards / Containers
- **Sections:** not cards. A Title-type heading sits on a 1 px ink rule with its aside (caption, Pencil) on the same line at the right; content follows directly on the sheet.
- **Title block:** a ruled grid with a 1 px ink frame and ink cell dividers; each cell has a lettered label over a body-small value, 6 px by 12 px padding. Used for the sheet's totals and for a lead's reference facts.
- **Board cards:** Clean Film, 1 px Survey Line border, square, 10 px padding, no shadow; a grab cursor shows they can be dragged.
- **Alerts:** 2 px radius, 1 px border, Clean Film. Errors set their text in Failure Red; cautions use the Straw plate, Ochre text and an Ochre border at 40%.
- **Live frames:** research in progress sits in a 1 px Survey Blue frame on Clean Film. Drop zones and framed empty states are dashed Control Line frames; a drop zone turns Survey Blue on a Blue Wash while something is dragged over it.

### Inputs / Fields
- **Style:** 32 px tall (28 px in the filter bar), transparent on the sheet, 1 px Control Line stroke, 2 px radius, 10 px side padding, Body type, Pencil placeholder. The search field insets a 16 px search icon 8 px from the left. Selects and textareas match; the caret is Survey Blue.
- **Focus:** the stroke turns Survey Blue with a 3 px Survey Blue ring at 50%.
- **Error / Disabled:** invalid fields take a Failure Red stroke and a 20% red ring; disabled is 50% opacity.
- **Checkbox:** a 16 px box in the same Control Line stroke with the same 2 px radius; checked fills with ink and a film check.

### Navigation
- **Rail:** ink fill, 208 px wide. The brand line is Title type over a rail-line rule. Items are Control type with 16 px line icons, 6 px by 10 px padding, square: Rail Film at rest, Rail Line fill on hover, a Survey Blue fill with white text when active. The Jobs entry at the foot swaps its icon for a spinner and shows the running job's title while work runs, with a "+N" count in Rail Pencil.
- **Tabs (lead page):** underline tabs in Control type, inactive at 60% ink, the active tab in full ink with a 2 px ink rule beneath, all sitting on a survey-line rule. On narrow widths the strip scrolls sideways and fades at its right edge.
- **Back link:** a small Pencil "Leads" link with a left arrow above the lead's name; it is navigation, not a kicker.

### Tier Zone (signature)
The tier as a zoning swatch: a 20 px square (16 px inside filters and title blocks) with a 1 px ink border and the lettered tier letter. A is Vermilion with a white letter, B is Signal Yellow with a Zone B Ink letter, and C is the grey hatch with its letter on a solid Drafting Film plate so it stays legible over the lines.

### Parcel Strip (signature)
The score drawn as a parcel. One lot per score component (need, ability, momentum, reach), each lot as wide as its weight (30/30/20/20 by default), divided by 1 px ink lines inside a 1 px ink frame, each filled from the left to the share it earned in the lead's tier colour. In sheet rows it is 96 by 12 px beside the score figure; in panels it runs full width at 28 px with a faint ink hatch over the fill, and lettered lot names with their value over weight sit beneath.

### Web-State Glyphs (signature)
What stands on the plot, as a 12 px glyph beside a body-small label, drawn with 1 px ink: a dashed square is vacant (no website), a square with three diagonal hatch lines is a social page only, a crossed square is a broken link, a square with a horizontal bar is a site that blocks checks, a dotted Survey Grey square is not audited, and a solid Verified Green square is a working site. A tooltip spells out what it means.

### Reach marks
Four 14 px line icons (phone, WhatsApp, email, social). Present ones are ink at a 2 px stroke; missing ones stay visible in Survey Grey at 1.5 px, so a gap reads as a gap. A tooltip names each.

### Ranked Sheet (signature)
The leads table. A sticky header of lettered column heads on Drafting Film with a 1 px ink rule beneath; sortable heads add a 12 px arrow and turn ink when active. Rows are top-aligned, separated by survey lines, with 8 px cells: plot number (right-aligned, plot-number lettering, Pencil), tier zone, score figure plus parcel strip, the name in semibold with its reason line in caption Pencil beneath (one line from 1280 px, two below), web state, reach marks, status stamp with any non-active verdict mark. Hover fills Film Shade at 60%; the selected row fills Survey Blue Wash. A rejected row keeps its place in the ranking, struck: the name gets a 1 px line-through, text drops to Pencil, the score to regular weight, and the tier zone and parcel strip fade to 50%. Excluded places (chains, duplicates), revealed with Show excluded, join the sheet struck the same way, with the exclusion reason as their reason line.

### Plot Panel (signature)
The selected plot, under the title block in the right column (or opened in place under its row). The name in semibold; a meta row under it with the plot number, status stamp, verdict mark and "Not researched yet" when true; the score with its tier zone, the full-width parcel strip and lettered lots; a lettered "Why it fits" list with Survey Grey bullets; a ruled facts list (lettered terms, values, verify links); and the action row: Approve as the primary button, Reject and Open as outline buttons. Missing data is stated in Pencil ("None in the map data"), never hidden.

### The Block (signature)
On the lead page, the lead's 500 m neighbourhood drawn from real coordinates: a square figure on Clean Film in a 1 px ink frame, with dashed survey-line distance rings at the full and half radius, a survey-line crosshair, lettered ring labels, a north arrow and a 100 m scale bar in ink. Each neighbour is drawn in exactly the web-glyph language, in ink on the sheet colour: dashed square for no website, a square with three diagonal ink lines for a social page, a crossed square for a broken link, a square with a 2 px ink bar for a blocked site, a dotted Survey Grey square when not audited, and the solid Verified Green square, the only fill, for a working site. Marks grow on hover or focus and link to their own page; a same-cuisine neighbour gets a second ink square around it; the lead itself is the centre plot, filled in its tier colour with a 2 px ink outline. A legend in the glyphs and a table of the nearest neighbours sit beside it.

### Jobs Drawer
A right-hand sheet on Overlay Film with the large overlay shadow, full width on a phone and up to 36rem otherwise, headed by a title on an ink rule. Each job is a row with its status mark, title and tabular age; the open job shows its steps (a small Survey Grey box while pending, a Survey Blue spinner while running, green check when done, red X on failure) and a live log in a Clean Film box in caption type, warnings in Ochre and errors in Failure Red.

## Do's and Don'ts

### Do:
- **Do** give every lead its stable plot number in plot-number lettering, in a meta row under the name or in a ruled title-block cell.
- **Do** show tier with the Tier Zone and score with the Parcel Strip, and keep the reason (the reason line or the "Why it fits" list) in the same row or panel as the score.
- **Do** use Survey Blue (#2b62a8) for every live state (selection, focus, the active rail item, running jobs, drop targets) and its wash (#dbe5f2) for live fills.
- **Do** draw divisions with 1 px lines: Plan Ink for the plan's structure, Survey Line (#c3c9c1) between items.
- **Do** strike rejected and excluded leads in place: line-through name, Pencil text, regular-weight score, 50% tier zone and parcel strip; a rejected lead keeps its rank.
- **Do** set labels, column heads, codes and stamps in plan lettering (600, 0.6875rem, uppercase, 0.07em, 72% width) and keep every figure tabular.
- **Do** keep absent data visible and labelled: faint Survey Grey marks for missing reach, "None in the map data" in Pencil for missing facts.
- **Do** stroke inputs, selects, checkboxes, toggles and dashed drop or empty frames in Control Line (#7f8a80), and keep Survey Grey (#a9b2a8) for absence only.
- **Do** keep the plan's marks square (0 radius) and controls at 2 px.

### Don't:
- **Don't** put kickers or eyebrows above headings; identifiers like the plot number go in a meta row under the name or in a ruled title block.
- **Don't** colour web states. The glyph's shape carries the state in ink; the green fill is reserved for a verified working site.
- **Don't** use Vermilion, Signal Yellow or the grey hatch for anything except tiers A, B and C; failures are Failure Red (#b0351f), cautions Ochre on Straw.
- **Don't** introduce a second live colour or use blue decoratively.
- **Don't** add shadows to the sheet, rows, cards or marks; shadows belong only to shadcn overlays (popovers, selects, menus, the jobs drawer).
- **Don't** round corners past 2 px or make pills.
- **Don't** remove a rejected lead from the sheet or re-rank it out of sight.
- **Don't** build the white CRM table with one accent and KPI cards on top; sheet totals live in the title block.
