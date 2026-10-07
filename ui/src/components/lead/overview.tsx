import { CheckIcon, MinusIcon, RotateCwIcon, XIcon } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router"

import { useJobsDrawer } from "@/components/jobs"
import { Bullets, Facts, Muted, Section, Sub } from "@/components/lead/parts"
import { Ext, Lettering, ParcelStrip, TierZone, WebGlyph } from "@/components/plan"
import { Button } from "@/components/ui/button"
import { startJob } from "@/lib/actions"
import { date, googleMaps, googleSearch, host, label, webState, type WebKind } from "@/lib/format"
import type { BlockPoint, Component, LeadDetail } from "@/lib/types"
import { cn } from "@/lib/utils"

const LOTS: { key: Component; name: string; means: string }[] = [
  { key: "need", name: "Need", means: "How weak their web presence is. No site, a dead link or a poor site all raise it." },
  { key: "ability", name: "Ability", means: "Signs of an established business: hours, cuisine, address and services on the map." },
  { key: "momentum", name: "Momentum", means: "Signs of activity: a social page, a recent survey date, listed hours." },
  { key: "reach", name: "Reach", means: "Ways to contact them: phone, WhatsApp, email, a map entry." },
]

export function ScoreSection({ lead }: { lead: LeadDetail }) {
  const s = lead.score
  return (
    <Section title="Sell score" aside={`Tier A from ${s.tier_a}, tier B from ${s.tier_b}${s.rich ? "" : " (no ratings in the map data)"}`}>
      <div className="flex items-baseline gap-2">
        <TierZone tier={s.tier} className="translate-y-0.5" />
        <span className="figure text-3xl leading-8 font-semibold">{s.total}</span>
        <Muted>of 100</Muted>
      </div>
      <ParcelStrip values={s} weights={s.weights} tier={s.tier} size="lg" className="mt-3 max-w-2xl" />
      <dl className="mt-1 flex max-w-2xl">
        {LOTS.map((l) => (
          <div key={l.key} style={{ flexGrow: s.weights[l.key], flexBasis: 0 }} className="min-w-0 pr-3">
            <Lettering as="dt">{l.name}</Lettering>
            <dd className="figure font-semibold">
              {s[l.key]}
              <span className="font-normal text-muted-foreground">/{s.weights[l.key]}</span>
            </dd>
            <dd className="mt-0.5 text-xs text-muted-foreground">{l.means}</dd>
          </div>
        ))}
      </dl>
      <Sub title="Why it ranks here" className="mt-5">
        {lead.excluded_reason ? (
          <p>
            Left out of the ranking: {lead.excluded_reason}. The score above is what it would get otherwise.
          </p>
        ) : (
          <Bullets items={s.reasons} empty="No positive signals were found in the map data." />
        )}
      </Sub>
    </Section>
  )
}

function Check({ value, good = 1 }: { value: number | null | undefined; good?: 0 | 1 }) {
  if (value === null || value === undefined) return <MinusIcon className="size-3.5 text-faint" aria-label="Unknown" />
  return value === good ? <CheckIcon className="size-3.5 text-good" aria-label="Yes" /> : <XIcon className="size-3.5 text-bad" aria-label="No" />
}

export function AuditSection({ lead }: { lead: LeadDetail }) {
  const drawer = useJobsDrawer()
  const [busy, setBusy] = useState(false)
  const a = lead.audit
  const uc = lead.url_check
  const state = webState(lead)
  const name = lead.place.name

  async function recheck() {
    setBusy(true)
    const job = await startJob(`/api/leads/${lead.key}/audit`)
    setBusy(false)
    if (job) drawer.open(job.id)
  }

  const verify = (
    <p className="mt-2 flex flex-wrap gap-x-4">
      <Ext href={googleSearch(name, lead.place.area)}>Search Google</Ext>
      <Ext href={googleMaps(name, lead.place.lat, lead.place.lng)}>Open in Google Maps</Ext>
    </p>
  )

  return (
    <Section
      title="Web presence"
      aside={a ? `Audited ${date(a.audited_at)}` : undefined}
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-2 text-base font-semibold">
          <WebGlyph kind={state.kind} className="size-3.5" />
          {state.text}
        </span>
        <Button variant="outline" size="sm" onClick={recheck} disabled={busy}>
          <RotateCwIcon data-icon="inline-start" />
          {a ? "Re-check" : "Audit now"}
        </Button>
      </div>
      <p className="prose-measure mt-1 text-muted-foreground">{state.detail}</p>

      {!a ? null : a.web_type === "none" ? (
        verify
      ) : a.web_type === "social_only" ? (
        <>
          <p className="mt-2">
            Listed page: <Ext href={lead.place.website} />
          </p>
          {verify}
        </>
      ) : (
        <>
          <Facts
            className="mt-3"
            rows={[
              ["Listed", <Ext href={uc?.url ?? lead.place.website}>{host(uc?.url ?? lead.place.website) || lead.place.website}</Ext>],
              ["Resolves to", a.final_url && a.final_url !== uc?.url ? <Ext href={a.final_url}>{host(a.final_url)}</Ext> : null],
              ["Link check", uc ? `${label(uc.status)}${uc.http_code ? ` (HTTP ${uc.http_code})` : ""}${uc.note ? `: ${uc.note}` : ""}` : null],
              ["Name on site", uc?.name_match === 1 ? "Matches the restaurant" : uc?.name_match === 0 ? "Does not mention the restaurant's name" : null],
              ["Web score", `${a.web_score} of 100 (higher is a better site)`],
            ]}
          />
          {a.http_ok ? (
            <ul className="mt-4 grid max-w-2xl grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
              {(
                [
                  ["HTTPS", a.https],
                  ["Mobile viewport", a.viewport],
                  ["Page title", a.has_title],
                  ["Meta description", a.has_meta_desc],
                  ["H1 heading", a.has_h1],
                  ["Menu on the site", a.has_menu_text],
                  ["WhatsApp link", a.has_whatsapp],
                  ["Click-to-call", a.has_tel],
                  ["Reservations", a.has_reserve],
                  ["Online ordering", a.has_order],
                  ["Structured data", a.has_schema],
                ] as [string, number | null][]
              ).map(([k, v]) => (
                <li key={k} className="flex items-center gap-2">
                  <Check value={v} />
                  {k}
                </li>
              ))}
              <li className="flex items-center gap-2">
                <Check value={a.cheap_builder} good={0} />
                {a.cheap_builder ? "On a free site-builder domain" : "Own domain"}
              </li>
              {a.mobile_perf !== null ? (
                <li className="figure">Mobile speed (PageSpeed): {Math.round(a.mobile_perf)} of 100</li>
              ) : (
                <li className="text-muted-foreground">Mobile speed: not measured</li>
              )}
              {a.copyright_year ? <li className="figure">Copyright year on site: {a.copyright_year}</li> : null}
              {a.page_kb ? <li className="figure">Page weight: {Math.round(a.page_kb)} KB</li> : null}
            </ul>
          ) : null}
          {a.issues.length ? (
            <Sub title="Issues found" className="mt-4">
              <Bullets items={a.issues} />
            </Sub>
          ) : null}
        </>
      )}
    </Section>
  )
}

const WEB_KIND: Record<BlockPoint["web"], WebKind> = {
  working: "built",
  broken: "broken",
  blocked: "blocked",
  social_only: "social",
  none: "vacant",
  unknown: "unknown",
}
const WEB_TEXT: Record<BlockPoint["web"], string> = {
  working: "working website",
  broken: "broken link",
  blocked: "site blocks checks",
  social_only: "social page only",
  none: "no website",
  unknown: "not audited",
}

// research.competitors() reports a neighbour's audit type when it has no working site.
const NEAREST_WEB: Record<string, string> = { none: "No website", social_only: "Social page only", website: "Site not working", unknown: "Not audited" }

function PlotMark({ p, size }: { p: BlockPoint; size: number }) {
  const h = size / 2
  const kind = WEB_KIND[p.web]
  const stroke = "var(--ink)"         // the shape carries the state, as in the sheet and the legend
  const common = { x: p.dx - h, y: -p.dy - h, width: size, height: size, vectorEffect: "non-scaling-stroke" as const }
  return (
    <>
      {kind === "built" ? (
        <rect {...common} fill="var(--good)" stroke="var(--good)" />
      ) : (
        <rect {...common} fill="var(--background)" stroke={kind === "unknown" ? "var(--faint)" : stroke} strokeDasharray={kind === "vacant" ? "3 2" : undefined} />
      )}
      {kind === "social" ? (
        <path
          d={`M${p.dx - h} ${-p.dy}l${h} ${-h}M${p.dx - h} ${-p.dy + h}l${size} ${-size}M${p.dx} ${-p.dy + h}l${h} ${-h}`}
          stroke={stroke}
          vectorEffect="non-scaling-stroke"
        />
      ) : null}
      {kind === "blocked" ? <path d={`M${p.dx - h / 2} ${-p.dy}h${h}`} stroke={stroke} strokeWidth={2} vectorEffect="non-scaling-stroke" /> : null}
      {kind === "broken" ? <path d={`M${p.dx - h} ${-p.dy - h}l${size} ${size}M${p.dx + h} ${-p.dy - h}l${-size} ${size}`} stroke={stroke} vectorEffect="non-scaling-stroke" /> : null}
      {p.same_cuisine ? <rect x={p.dx - h - 8} y={-p.dy - h - 8} width={size + 16} height={size + 16} fill="none" stroke="var(--ink)" vectorEffect="non-scaling-stroke" /> : null}
    </>
  )
}

/** The lead's block drawn from real coordinates: every other restaurant within the radius, marked by what stands on its plot. */
export function BlockPlot({ lead }: { lead: LeadDetail }) {
  const { radius_m: R, points } = lead.block
  const c = lead.competitors
  const [hover, setHover] = useState<BlockPoint | null>(null)
  if (!points) {
    return (
      <Section title="The block">
        <p className="text-muted-foreground">This place has no coordinates in the map data, so its surroundings cannot be drawn.</p>
      </Section>
    )
  }
  const shown = points.filter((p) => !p.chain)
  const working = shown.filter((p) => p.web === "working").length
  const pad = 60
  const box = R + pad
  const legend: [BlockPoint["web"], string][] = [
    ["none", "No website"],
    ["social_only", "Social page only"],
    ["working", "Working website"],
    ["broken", "Broken link"],
  ]
  return (
    <Section title="The block" aside={`${shown.length} restaurants within ${R} m, chains left out`}>
      <p className="prose-measure">
        {shown.length === 0
          ? `No other restaurant is mapped within ${R} m.`
          : `${working} of ${shown.length} neighbours have a working website${
              c.lead_cuisine && c.same_cuisine_nearby ? `; ${c.same_cuisine_with_working_website} of ${c.same_cuisine_nearby} serving ${c.lead_cuisine} do` : ""
            }.`}
      </p>
      <div className="mt-3 grid gap-5 lg:grid-cols-[minmax(0,26rem)_1fr]">
        <figure>
          <svg
            viewBox={`${-box} ${-box} ${box * 2} ${box * 2}`}
            className="aspect-square w-full border border-rule bg-card"
            role="img"
            aria-label={`Plot of ${shown.length} restaurants within ${R} metres of ${lead.place.name}. ${working} have a working website.`}
          >
            {[R, R / 2].map((r) => (
              <circle key={r} r={r} fill="none" stroke="var(--border)" strokeDasharray="6 5" vectorEffect="non-scaling-stroke" />
            ))}
            <path d={`M${-R} 0H${R}M0 ${-R}V${R}`} stroke="var(--border)" vectorEffect="non-scaling-stroke" />
            <text x={6} y={-R / 2 - 6} className="lettering fill-muted-foreground" style={{ fontSize: 30 }}>
              {R / 2} m
            </text>
            <text x={6} y={-R - 6} className="lettering fill-muted-foreground" style={{ fontSize: 30 }}>
              {R} m
            </text>
            {/* north arrow and scale bar, as on any plan */}
            <g transform={`translate(${box - 34} ${-box + 62})`} stroke="var(--ink)" fill="none" vectorEffect="non-scaling-stroke">
              <path d="M0 22V-14M-7 -4 0 -14 7 -4" vectorEffect="non-scaling-stroke" />
              <text y={-20} textAnchor="middle" stroke="none" className="lettering fill-foreground" style={{ fontSize: 30 }}>
                N
              </text>
            </g>
            <g transform={`translate(${-box + 20} ${box - 22})`}>
              <path d="M0 -6V0H100V-6" fill="none" stroke="var(--ink)" vectorEffect="non-scaling-stroke" />
              <text x={108} y={2} className="lettering fill-foreground" style={{ fontSize: 30 }}>
                100 m
              </text>
            </g>
            {shown.map((p) => (
              <Link
                key={p.key}
                to={`/leads/${p.key}`}
                aria-label={`${p.name}, ${p.distance_m} metres, ${WEB_TEXT[p.web]}`}
                onMouseEnter={() => setHover(p)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(p)}
                onBlur={() => setHover(null)}
              >
                <rect x={p.dx - 22} y={-p.dy - 22} width={44} height={44} fill="transparent" />
                <PlotMark p={p} size={hover?.key === p.key ? 34 : 26} />
              </Link>
            ))}
            <rect x={-19} y={-19} width={38} height={38} fill={`var(--zone-${lead.score.tier === "A" ? "a" : lead.score.tier === "B" ? "b" : "c"})`} stroke="var(--ink)" strokeWidth={2} vectorEffect="non-scaling-stroke" />
          </svg>
          <figcaption className="mt-1 min-h-5 text-xs text-muted-foreground" aria-live="polite">
            {hover ? `${hover.name} · ${hover.distance_m} m · ${WEB_TEXT[hover.web]}${hover.cuisine ? ` · ${hover.cuisine}` : ""}` : "This lead is the filled plot at the centre. Hover or tab to a neighbour to name it; click to open it."}
          </figcaption>
        </figure>
        <div>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[0.8125rem]">
            {legend.map(([k, text]) => (
              <li key={k} className="inline-flex items-center gap-1.5">
                <WebGlyph kind={WEB_KIND[k]} />
                {text}
              </li>
            ))}
            {c.lead_cuisine ? (
              <li className="inline-flex items-center gap-1.5">
                <span className="grid size-4 place-items-center border border-rule">
                  <span className="size-1.5 bg-foreground" />
                </span>
                Same cuisine ({c.lead_cuisine})
              </li>
            ) : null}
          </ul>
          {c.nearest?.length ? (
            <table className="mt-3 w-full border-collapse text-[0.8125rem]">
              <caption className="lettering pb-1 text-left text-muted-foreground">{c.same_cuisine_nearby ? "Nearest with the same cuisine" : "Nearest neighbours"}</caption>
              <tbody>
                {c.nearest.map((n, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="py-1 pr-3">{n.name}</td>
                    <td className="figure py-1 pr-3 text-right whitespace-nowrap text-muted-foreground">{n.distance_m} m</td>
                    <td className={cn("py-1 whitespace-nowrap", n.web === "working website" ? "text-good" : "text-muted-foreground")}>
                      {n.web === "working website" ? `Site ${n.web_score ?? ""}/100` : (NEAREST_WEB[n.web] ?? label(n.web))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      </div>
    </Section>
  )
}

const TAG_ORDER = ["cuisine", "opening_hours", "phone", "contact:phone", "contact:whatsapp", "website", "contact:website", "contact:instagram", "contact:facebook", "email", "contact:email"]

const TAG_NAMES: Record<string, string> = { "addr:housenumber": "Number", "addr:street": "Street", "addr:postcode": "Postcode", "addr:city": "City", opening_hours: "Hours", "contact:whatsapp": "WhatsApp", "check_date": "Last checked" }
function tagName(k: string): string {
  return TAG_NAMES[k] ?? k.replace(/^(addr|contact):/, "").replace(/[:_]/g, " ")
}

export function MapFacts({ lead }: { lead: LeadDetail }) {
  const entries = Object.entries(lead.tags).filter(([k]) => k !== "name" && k !== "amenity")
  entries.sort(([a], [b]) => {
    const ia = TAG_ORDER.indexOf(a)
    const ib = TAG_ORDER.indexOf(b)
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b)
  })
  return (
    <Section title="On the map" aside={lead.place.fetched_at ? `OpenStreetMap, fetched ${date(lead.place.fetched_at)}` : undefined}>
      {entries.length ? (
        <Facts rows={entries.map(([k, v]) => [tagName(k), /^https?:\/\//.test(v) ? <Ext href={v} /> : v.replace(/;/g, ", ")])} />
      ) : (
        <p className="text-muted-foreground">The map entry has a name and a position and nothing else. That is common in Colombia and is why scores here are only a first filter.</p>
      )}
    </Section>
  )
}
