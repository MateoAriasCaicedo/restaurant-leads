# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Chosen by the user: React, built with the project's installed skills (shadcn/ui, impeccable, Vercel React practices). Concretely: Vite + React + TypeScript + Tailwind v4 + shadcn/ui on Base UI in `ui/`, talking to a local Python API (Starlette, `server/`) that wraps the existing pipeline modules and SQLite file. No hosting: it runs on the user's own PC.

## Users

One person: the owner of Daan Agency, a solo web designer and developer in Medellín who sells websites, digital menus and local SEO to independent restaurants. They use the app alone, at their desk, on a laptop or desktop screen. There are no accounts, roles or sharing.

## Product Purpose

Decide who to pitch next. The app ranks the restaurants of a neighborhood by how much they need a website and how reachable and established they are, so a session ends with a short list worth approving and researching. Detail pages, research and outreach tracking exist to support that decision and what follows from it.

Success: after one sitting the user knows which few restaurants to contact this week and why each one is a fit.

## Positioning

The list is built from evidence the user did not have to gather by hand: every restaurant in an area from OpenStreetMap, an automated audit of each one's web presence, and a transparent score (need, ability, momentum, reach) with the reasons spelled out. For any single restaurant, one click runs a researched profile (menu, reputation, operating status, competitors nearby, a build plan and pitch hooks). A generic CRM starts from contacts the user already has; this starts from a neighborhood.

## Operating Context

- Pipeline stages the user runs: discover an area, audit websites, score, approve a lead, add photos or notes, get insights, review the profile, contact, log the outcome.
- Lead statuses: approved, enriched, ready, contacted, rejected.
- Data comes from OpenStreetMap, which is patchy in Colombia. "No website" can be a data gap, so leads are verified (Google, Maps) before outreach. Ratings and review counts are usually absent.
- Research on one restaurant runs through the user's Claude subscription, one restaurant per explicit request, and takes minutes.
- Instagram and Google Maps are never scraped. The user drops screenshots and pasted notes into a lead by hand.
- Outreach is by WhatsApp, phone, Instagram, email or a visit, and must respect Colombia's Ley 1581 (stop contacting anyone who opts out).
- Restaurant names, dishes and quoted copy are Spanish; the interface and the written analysis are English.

## Capabilities and Constraints

- Ranked table of leads with filters and search; excluded places (chains, duplicates) viewable with the reason.
- Lead detail: score breakdown and reasons, website audit, competitors within 500 m, researched profile, menu, online presence, build plan, materials.
- Status changes, a private note and a contact log per lead, and a board grouped by status.
- Running discover (per area) and audit from the app with a live log; one analysis at a time, never in batch.
- Photo, menu and notes upload per lead.
- Local only: bound to 127.0.0.1, desktop-first. No map view in this version.
- Scores are a first filter, not a verdict. Of 235 places currently loaded, 216 have no website and 2 have a researched profile, so "not researched yet" is the normal state of a lead.
- All analysis text comes from a model reading public web content and is treated as untrusted when shown.

## Brand Commitments

- Name shown in the app: Daan Agency.
- No logo, palette or typeface has been provided.

## Evidence on Hand

- `leads.db`: 235 restaurants in Laureles, all audited; 221 ranked (8 tier A, 35 tier B, 178 tier C), 14 excluded.
- Two researched leads with real profiles and menus: Naan Laureles and Rico Ajiaco y Algo más (`leads/`).
- Real dropped-in material for Rico Ajiaco: 2 Instagram photos and 5 menu screenshots.
- No testimonials, client results, pricing or conversion figures exist. Do not invent any.

## Product Principles

1. The reason comes with the rank. A score is never shown without why.
2. Say what is unknown. Missing data, unverified claims and low-confidence findings are labelled, never smoothed over.
3. One restaurant at a time gets the expensive attention. Research is a deliberate act, not a background process.
4. The user's judgment closes the loop. The app proposes; verifying and deciding stay with the person.
5. Respect the restaurant. Public data only, and an opt-out ends contact.
