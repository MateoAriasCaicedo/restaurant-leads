import { ArrowDownIcon, ArrowUpIcon, ArrowUpRightIcon, DownloadIcon, SearchIcon } from "lucide-react"
import { Fragment, useDeferredValue, useEffect, useMemo, useRef, type KeyboardEvent, type ReactNode } from "react"
import { Link, useNavigate, useSearchParams } from "react-router"

import { useJobsDrawer } from "@/components/jobs"
import { Ext, Lettering, ParcelStrip, Reach, STATUS_HELP, StatusStamp, TierZone, VerdictMark, WebState } from "@/components/plan"
import { Alert, AlertAction, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button, buttonVariants } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useLeads, useMeta } from "@/hooks/use-data"
import { setStatus, startJob, unreject } from "@/lib/actions"
import { message } from "@/lib/api"
import { ago, areaName, compareText, date, googleMaps, googleSearch, host, humanize, label, norm, plotNo, webState, withScheme } from "@/lib/format"
import type { Component, LeadList, LeadRow, Meta, Tier } from "@/lib/types"
import { cn } from "@/lib/utils"

const WEB_FILTERS = [
  { value: "any", label: "Any web presence" },
  { value: "vacant", label: "No website" },
  { value: "social", label: "Social page only" },
  { value: "broken", label: "Broken or blocked link" },
  { value: "built", label: "Working website" },
  { value: "unknown", label: "Not audited" },
]
type SortKey = "score" | "name" | "contact"
const DEFAULT_WEIGHTS: Record<Component, number> = { need: 30, ability: 30, momentum: 20, reach: 20 }

function useFilters() {
  const [params, setParams] = useSearchParams()
  const set = (patch: Record<string, string | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        for (const [k, v] of Object.entries(patch)) {
          if (v === null || v === "") next.delete(k)
          else next.set(k, v)
        }
        return next
      },
      { replace: true },
    )
  return {
    q: params.get("q") ?? "",
    tiers: (params.get("tier") ?? "").split("").filter((t): t is Tier => "ABC".includes(t)),
    web: params.get("web") ?? "any",
    status: params.get("status") ?? "any",
    area: params.get("area") ?? "any",
    phone: params.get("phone") === "1",
    excluded: params.get("excluded") === "1",
    premium: params.get("premium") === "1",
    sort: (params.get("sort") ?? "score") as SortKey,
    dir: params.get("dir") === "asc" ? "asc" : "desc",
    sel: params.get("sel"),
    set,
    active: ["q", "tier", "web", "status", "area", "phone", "excluded", "premium"].some((k) => params.has(k)),
    clear: () => setParams((prev) => new URLSearchParams(prev.has("sel") ? { sel: prev.get("sel")! } : {}), { replace: true }),
  }
}

function webKind(r: LeadRow) {
  const k = webState(r).kind
  return k === "blocked" ? "broken" : k
}

export default function LeadsPage() {
  const { data, error, isLoading, mutate } = useLeads()
  const { data: meta } = useMeta()
  const f = useFilters()
  const navigate = useNavigate()
  const q = useDeferredValue(f.q)
  const search = useRef<HTMLInputElement>(null)
  const tableBox = useRef<HTMLDivElement>(null)
  const weights = meta?.weights ?? DEFAULT_WEIGHTS

  // The filters live in the URL, so they arrive as fresh objects each render: memoize on their primitive values.
  const { web, status, area, phone, excluded, premium, sort, dir } = f
  const tierKey = f.tiers.join("")
  const rows = useMemo(() => {
    if (!data) return []
    const needle = norm(q.trim())
    const pool = excluded ? [...data.rows, ...data.hidden] : data.rows
    const out = pool.filter((r) => {
      if (tierKey && !tierKey.includes(r.tier)) return false
      if (web !== "any" && webKind(r) !== web) return false
      if (status !== "any" && (r.status || "none") !== status) return false
      if (area !== "any" && r.area !== area) return false
      if (phone && !r.phone) return false
      if (premium && !r.quality_tier) return false
      if (needle && !norm(`${r.name} ${r.cuisine} ${r.address ?? ""} ${r.place_id}`).includes(needle)) return false
      return true
    })
    const sign = dir === "asc" ? 1 : -1
    if (sort === "name") out.sort((a, b) => sign * compareText(a.name, b.name))
    else if (sort === "contact") out.sort((a, b) => sign * ((a.last_contact?.at ?? 0) - (b.last_contact?.at ?? 0)))
    else if (premium && sort === "score") out.sort((a, b) => sign * (a.quality - b.quality)) // premium view: best quality first
    else if (dir === "asc") out.reverse() // the server already ranks best-first
    return out
  }, [data, q, tierKey, web, status, area, phone, premium, excluded, sort, dir])

  const selected = rows.find((r) => r.key === f.sel) ?? null
  // A column that is empty for every lead is noise: the contact column appears with the first logged contact.
  const showContact = data?.rows.some((r) => r.last_contact) ?? false
  const areas = meta?.areas.filter((a) => a.places > 0) ?? []

  useEffect(() => {
    function onKey(e: globalThis.KeyboardEvent) {
      const el = e.target as HTMLElement
      if (e.key === "/" && !/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) && !el.isContentEditable) {
        e.preventDefault()
        search.current?.focus()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  function select(key: string | null, scroll = false) {
    f.set({ sel: key })
    if (key && scroll) {
      requestAnimationFrame(() => tableBox.current?.querySelector(`[data-key="${key}"]`)?.scrollIntoView({ block: "nearest" }))
    }
  }

  function onTableKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.target !== e.currentTarget && (e.target as HTMLElement).closest("a,button,input")) return
    const i = selected ? rows.indexOf(selected) : -1
    if (e.key === "ArrowDown" || e.key === "j") {
      e.preventDefault()
      if (rows[i + 1]) select(rows[i + 1].key, true)
    } else if (e.key === "ArrowUp" || e.key === "k") {
      e.preventDefault()
      if (rows[Math.max(0, i - 1)]) select(rows[Math.max(0, i - 1)].key, true)
    } else if (selected && e.key === "Enter") {
      void navigate(`/leads/${selected.key}`)
    } else if (selected && !selected.excluded_reason && !selected.status && e.key === "a") {
      void setStatus(selected.key, "approved", { from: null, name: selected.name })
    } else if (selected && !selected.excluded_reason && selected.status !== "rejected" && e.key === "x") {
      void setStatus(selected.key, "rejected", { from: selected.status || null, name: selected.name })
    } else if (selected && e.key === "u") {
      // undo only what the keys do: a rejection goes back to its earlier status, an approval to none
      if (selected.status === "rejected") void unreject(selected.key, selected.name)
      else if (selected.status === "approved") void setStatus(selected.key, null, { from: "approved", name: selected.name })
    }
  }

  function sortBy(key: SortKey) {
    if (f.sort === key) f.set({ dir: f.dir === "asc" ? "desc" : "asc" })
    else f.set({ sort: key === "score" ? null : key, dir: key === "name" ? "asc" : null })
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-rule px-4 py-2.5">
        <h1 className="sr-only">Leads</h1>
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            ref={search}
            type="search"
            value={f.q}
            onChange={(e) => f.set({ q: e.target.value })}
            placeholder="Search name, cuisine, address"
            aria-label="Search leads (press / to focus)"
            className="w-64 pl-8"
          />
        </div>
        <ToggleGroup
          multiple
          value={f.tiers}
          onValueChange={(v) => f.set({ tier: (v as string[]).sort().join("") })}
          variant="outline"
          size="sm"
          spacing={0}
          aria-label="Tier"
        >
          {(["A", "B", "C"] as Tier[]).map((t) => (
            <ToggleGroupItem key={t} value={t} aria-label={`Tier ${t}`} className="gap-1.5 data-pressed:bg-live-soft">
              <TierZone tier={t} className="size-4" />
              <span className="figure">{data?.counts.tiers[t] ?? ""}</span>
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <Select value={f.web} onValueChange={(v) => f.set({ web: v === "any" ? null : (v as string) })} items={WEB_FILTERS}>
          <SelectTrigger size="sm" aria-label="Web presence">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {WEB_FILTERS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
        <StatusFilter value={f.status} onChange={(v) => f.set({ status: v === "any" ? null : v })} meta={meta} />
        {areas.length > 1 ? (
          <Select
            value={f.area}
            onValueChange={(v) => f.set({ area: v === "any" ? null : (v as string) })}
            items={[{ value: "any", label: "All areas" }, ...areas.map((a) => ({ value: a.key, label: areaName(a.key) }))]}
          >
            <SelectTrigger size="sm" aria-label="Area">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="any">All areas</SelectItem>
                {areas.map((a) => (
                  <SelectItem key={a.key} value={a.key}>
                    {areaName(a.key)}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        ) : null}
        <Label className="gap-1.5 font-normal">
          <Checkbox checked={f.phone} onCheckedChange={(c) => f.set({ phone: c ? "1" : null })} />
          Has phone
        </Label>
        <Label className="gap-1.5 font-normal" title="High-quality restaurants: Maps-verified premium plus OSM candidates. Run `python quality.py --scrape 10` to verify more.">
          <Checkbox checked={f.premium} onCheckedChange={(c) => f.set({ premium: c ? "1" : null })} />
          Premium
          {data ? <span className="figure text-muted-foreground">{data.counts.premium}+{data.counts.candidates}</span> : null}
        </Label>
        <Label className="gap-1.5 font-normal">
          <Checkbox checked={f.excluded} onCheckedChange={(c) => f.set({ excluded: c ? "1" : null })} />
          Show excluded
        </Label>
        {f.active ? (
          <Button variant="ghost" size="sm" onClick={f.clear}>
            Clear filters
          </Button>
        ) : null}
        <div className="ml-auto flex items-center gap-3">
          {data ? (
            <span className="figure text-muted-foreground" aria-live="polite">
              {rows.length === data.rows.length && !f.excluded ? `${rows.length} plots` : `${rows.length} of ${data.rows.length + (f.excluded ? data.hidden.length : 0)}`}
            </span>
          ) : null}
          <a href="/api/export/leads.csv" className={buttonVariants({ variant: "outline", size: "sm" })}>
            <DownloadIcon data-icon="inline-start" />
            CSV
          </a>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <div
          ref={tableBox}
          tabIndex={0}
          role="region"
          aria-label="Ranked leads. Arrow keys move, Enter opens, A approves, X rejects, U clears the status."
          onKeyDown={onTableKey}
          className="min-w-0 flex-1 overflow-auto outline-offset-[-2px]"
        >
          {data ? <TitleStrip data={data} meta={meta} /> : null}
          {meta && meta.unaudited > 0 ? <UnauditedBanner count={meta.unaudited} /> : null}
          {error ? (
            <Alert variant="destructive" className="m-4 w-auto">
              <AlertTitle>The leads could not be loaded</AlertTitle>
              <AlertDescription>{message(error)}</AlertDescription>
              <AlertAction>
                <Button variant="outline" size="sm" onClick={() => void mutate()}>
                  Try again
                </Button>
              </AlertAction>
            </Alert>
          ) : isLoading ? (
            <div className="flex flex-col gap-px p-4">
              {Array.from({ length: 12 }, (_, i) => (
                <Skeleton key={i} className="h-11 w-full" />
              ))}
            </div>
          ) : data && data.counts.places === 0 ? (
            <Empty className="h-full">
              <EmptyHeader>
                <EmptyTitle>No area has been surveyed yet</EmptyTitle>
                <EmptyDescription>
                  Discover an area to pull its restaurants from OpenStreetMap, then audit their websites. The ranked sheet fills in from there.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <Link to="/pipeline" className={buttonVariants()}>
                  Go to Pipeline
                </Link>
              </EmptyContent>
            </Empty>
          ) : rows.length === 0 ? (
            <Empty className="h-full">
              <EmptyHeader>
                <EmptyTitle>No plots match these filters</EmptyTitle>
                <EmptyDescription>Loosen a filter, or clear them to see the whole sheet again.</EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <Button variant="outline" onClick={f.clear}>
                  Clear filters
                </Button>
              </EmptyContent>
            </Empty>
          ) : (
            <table className="w-full border-collapse">
              <thead className="sticky top-0 z-10 bg-background">
                <tr className="text-left shadow-[inset_0_-1px_0_var(--rule)]">
                  <Th className="hidden pl-4 text-right md:table-cell">Plot</Th>
                  <Th className="pl-4 md:pl-2">Tier</Th>
                  <SortTh label="Score" k="score" f={f} onSort={sortBy} />
                  <SortTh label="Name and why it fits" k="name" f={f} onSort={sortBy} className="w-full min-w-44 sm:min-w-56" />
                  <Th>On the plot</Th>
                  <Th>Reach</Th>
                  <Th className={showContact ? undefined : "pr-4"}>Status</Th>
                  {showContact ? <SortTh label="Last contact" k="contact" f={f} onSort={sortBy} className="pr-4" /> : null}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <Fragment key={r.key}>
                    <Row r={r} weights={weights} selected={r.key === f.sel} onSelect={() => select(r.key)} showContact={showContact} />
                    {r.key === f.sel ? (
                      // Without room for the side panel, the selected plot opens in place under its row.
                      <tr className="border-b border-rule bg-card xl:hidden">
                        <td colSpan={showContact ? 8 : 7} className="pt-3">
                          {/* pinned to the visible part of the sideways-scrolling table, never wider than the screen */}
                          <div className="sticky left-0 max-w-[min(36rem,100vw)]">
                            <PlotPanel r={r} weights={weights} />
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <aside className="hidden w-80 shrink-0 flex-col overflow-y-auto border-l border-rule xl:flex" aria-label="Selected plot">
          {data ? <TitleBlock data={data} meta={meta} /> : <Skeleton className="m-4 h-24" />}
          {selected ? <PlotPanel r={selected} weights={weights} /> : <PanelHint />}
        </aside>
      </div>
    </div>
  )
}

function Th({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <th scope="col" className={cn("lettering h-8 px-2 whitespace-nowrap text-muted-foreground", className)}>
      {children}
    </th>
  )
}

function SortTh({ label: text, k, f, onSort, className }: { label: string; k: SortKey; f: ReturnType<typeof useFilters>; onSort: (k: SortKey) => void; className?: string }) {
  const on = f.sort === k
  const Icon = f.dir === "asc" ? ArrowUpIcon : ArrowDownIcon
  return (
    <th scope="col" aria-sort={on ? (f.dir === "asc" ? "ascending" : "descending") : "none"} className={cn("h-8 px-2 whitespace-nowrap", className)}>
      <button type="button" onClick={() => onSort(k)} className={cn("lettering inline-flex items-center gap-1 hover:text-foreground", on ? "text-foreground" : "text-muted-foreground")}>
        {text}
        {on ? <Icon className="size-3" aria-hidden="true" /> : null}
      </button>
    </th>
  )
}

function StatusFilter({ value, onChange, meta }: { value: string; onChange: (v: string) => void; meta?: Meta }) {
  const items = [
    { value: "any", label: "Any status" },
    { value: "none", label: "No status yet" },
    ...(meta?.statuses ?? []).map((s) => ({ value: s as string, label: label(s) })),
  ]
  return (
    <Select value={value} onValueChange={(v) => onChange(v as string)} items={items}>
      <SelectTrigger size="sm" aria-label="Status">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          {items.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  )
}

function UnauditedBanner({ count }: { count: number }) {
  const drawer = useJobsDrawer()
  return (
    <Alert className="m-4 w-auto border-warn/40 bg-warn-soft text-warn">
      <AlertTitle>
        {count} {count === 1 ? "place has" : "places have"} not been audited
      </AlertTitle>
      <AlertDescription className="text-warn">
        Until the audit runs they are scored as if they had no website, so they rank higher than they should.
      </AlertDescription>
      <AlertAction>
        <Button
          size="sm"
          onClick={async () => {
            const job = await startJob("/api/jobs/audit", { refresh: false })
            if (job) drawer.open(job.id)
          }}
        >
          Run the audit
        </Button>
      </AlertAction>
    </Alert>
  )
}

function Row({ r, weights, selected, onSelect, showContact }: { r: LeadRow; weights: Record<Component, number>; selected: boolean; onSelect: () => void; showContact: boolean }) {
  const struck = r.status === "rejected" || !!r.excluded_reason
  return (
    <tr
      data-key={r.key}
      onClick={onSelect}
      aria-selected={selected}
      className={cn("cursor-default border-b border-border align-top", selected ? "bg-live-soft" : "hover:bg-muted/60", struck && "text-muted-foreground")}
    >
      <td className="plot-no hidden py-2 pr-2 pl-4 text-right text-xs leading-5 whitespace-nowrap text-muted-foreground md:table-cell">{plotNo(r.place_id)}</td>
      <td className="py-2 pr-2 pl-4 md:pl-2">
        <TierZone tier={r.tier} className={cn(struck && "opacity-50")} />
      </td>
      <td className="px-2 py-2">
        <div className="flex items-center gap-2">
          <span className={cn("figure w-6 text-right text-base leading-5 font-semibold", struck && "font-normal text-muted-foreground")}>{r.sell_score}</span>
          <ParcelStrip values={r} weights={weights} tier={r.tier} className={cn("hidden sm:flex", struck && "opacity-50")} />
        </div>
      </td>
      <td className="max-w-0 px-2 py-2">
        <Link
          to={`/leads/${r.key}`}
          onClick={(e) => e.stopPropagation()}
          className={cn("block truncate font-semibold hover:underline", struck ? "line-through decoration-1" : "text-foreground")}
        >
          {r.name}
          {r.quality_tier ? (
            <span
              className="figure ml-2 align-middle text-[0.6875rem] font-normal tracking-wide text-muted-foreground uppercase"
              title={`Quality ${r.quality}: ${r.quality_reasons.join("; ")}`}
            >
              {r.quality_tier === "premium" ? "★ premium" : "candidate"}
            </span>
          ) : null}
        </Link>
        <div className="line-clamp-2 text-xs leading-5 text-muted-foreground xl:line-clamp-1">{rowReason(r)}</div>
      </td>
      <td className="px-2 py-2 text-[0.8125rem] leading-5">
        <WebState state={webState(r)} />
      </td>
      <td className="px-2 py-2 leading-5">
        <Reach flags={r.reach_flags} />
      </td>
      <td className={cn("py-2 pl-2", showContact ? "pr-2" : "pr-4")}>
        <div className="flex items-center gap-1">
          <StatusStamp status={r.status} />
          {r.operating_status && r.operating_status !== "active" ? <VerdictMark verdict={r.operating_status} /> : null}
        </div>
      </td>
      {showContact ? (
        <td className="py-2 pr-4 pl-2 text-xs leading-5 whitespace-nowrap text-muted-foreground">
          {r.last_contact ? `${ago(r.last_contact.at)} · ${label(r.last_contact.outcome)}` : ""}
        </td>
      ) : null}
    </tr>
  )
}

// The web column already says what stands on the plot, so the row's reason line starts with what else fits.
const WEB_REASON = /^(no website|only social|website link)/

function rowReason(r: LeadRow): string {
  if (r.excluded_reason) return `Excluded from the ranking: ${r.excluded_reason}`
  const rest = r.reasons.filter((x) => !WEB_REASON.test(x)).map(humanize)
  return rest.length ? rest.join(" · ") : "No other signals on the map"
}

/** The title block's facts as one ruled line, for widths where the side panel is hidden. */
function TitleStrip({ data, meta }: { data: LeadList; meta?: Meta }) {
  const surveyed = meta?.areas.filter((a) => a.places > 0) ?? []
  const latest = Math.max(0, ...surveyed.map((a) => a.fetched_at ?? 0))
  const facts: [string, ReactNode][] = [
    ["Area", surveyed.map((a) => areaName(a.key)).join(", ") || "None yet"],
    ["Plots", data.counts.places],
    ["Ranked", data.counts.scored],
    ["Researched", data.counts.profiled],
    ["Surveyed", latest ? date(latest) : ""],
  ]
  return (
    <dl className="flex flex-wrap gap-x-5 gap-y-1 border-b border-border px-4 py-2 text-[0.8125rem] xl:hidden">
      {facts.map(([k, v]) => (
        <div key={k} className="flex items-baseline gap-1.5">
          <Lettering as="dt">{k}</Lettering>
          <dd className="figure font-semibold">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

function TitleBlock({ data, meta }: { data: LeadList; meta?: Meta }) {
  const surveyed = meta?.areas.filter((a) => a.places > 0) ?? []
  const latest = Math.max(0, ...surveyed.map((a) => a.fetched_at ?? 0))
  const cell = "border-rule px-3 py-1.5"
  return (
    <dl className="m-4 grid grid-cols-3 border border-rule text-[0.8125rem]">
      <div className={cn(cell, "col-span-2 border-r border-b")}>
        <Lettering as="dt">Area</Lettering>
        <dd className="truncate font-semibold">{surveyed.map((a) => areaName(a.key)).join(", ") || "None yet"}</dd>
      </div>
      <div className={cn(cell, "border-b")}>
        <Lettering as="dt">Surveyed</Lettering>
        <dd className="figure">{latest ? date(latest) : ""}</dd>
      </div>
      <div className={cn(cell, "border-r border-b")}>
        <Lettering as="dt">Plots</Lettering>
        <dd className="figure font-semibold">{data.counts.places}</dd>
      </div>
      <div className={cn(cell, "border-r border-b")}>
        <Lettering as="dt">Ranked</Lettering>
        <dd className="figure font-semibold">{data.counts.scored}</dd>
      </div>
      <div className={cn(cell, "border-b")}>
        <Lettering as="dt">Researched</Lettering>
        <dd className="figure font-semibold">{data.counts.profiled}</dd>
      </div>
      {(["A", "B", "C"] as Tier[]).map((t, i) => (
        <div key={t} className={cn(cell, "flex items-center gap-2", i < 2 && "border-r")}>
          <dt>
            <TierZone tier={t} />
          </dt>
          <dd className="figure font-semibold">{data.counts.tiers[t]}</dd>
        </div>
      ))}
    </dl>
  )
}

function PanelHint() {
  return (
    <div className="px-4 pb-4 text-muted-foreground">
      <p className="text-foreground">Select a plot to see why it ranks where it does.</p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[0.8125rem]">
        {(
          [
            [
              <>
                <ArrowUpIcon className="size-3" aria-label="Up" />
                <ArrowDownIcon className="size-3" aria-label="Down" />
              </>,
              "Move through the sheet",
            ],
            ["Enter", "Open the lead"],
            ["A", "Approve for research"],
            ["X", "Reject (with undo)"],
            ["U", "Undo a reject or an approval"],
            ["/", "Search"],
          ] as [ReactNode, string][]
        ).map(([k, v]) => (
          <div key={v} className="contents">
            <dt>
              <kbd className="lettering inline-flex h-5 min-w-6 items-center justify-center gap-0.5 border border-input px-1 text-foreground">{k}</kbd>
            </dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function PlotPanel({ r, weights }: { r: LeadRow; weights: Record<Component, number> }) {
  const site = r.website ? withScheme(r.website) : null
  const lots: [Component, string][] = [
    ["need", "Need"],
    ["ability", "Ability"],
    ["momentum", "Momentum"],
    ["reach", "Reach"],
  ]
  return (
    <div className="flex flex-col gap-4 px-4 pb-6">
      <div>
        <h2 className="text-lg leading-6 font-semibold">{r.name}</h2>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <span className="plot-no text-xs text-muted-foreground">{plotNo(r.place_id)}</span>
          <StatusStamp status={r.status} />
          <VerdictMark verdict={r.operating_status} />
          {r.has_profile ? null : <span className="text-xs text-muted-foreground">Not researched yet</span>}
        </div>
      </div>

      <div>
        <div className="flex items-baseline gap-2">
          <TierZone tier={r.tier} className="translate-y-0.5" />
          <span className="figure text-2xl leading-7 font-semibold">{r.sell_score}</span>
          <span className="text-muted-foreground">of 100</span>
        </div>
        <ParcelStrip values={r} weights={weights} tier={r.tier} size="lg" className="mt-2" />
        <dl className="mt-1.5 grid grid-cols-4 gap-x-2 text-xs">
          {lots.map(([k, name]) => (
            <div key={k} className="min-w-0">
              <Lettering as="dt">{name}</Lettering>
              <dd className="figure">
                {r[k]}
                <span className="text-muted-foreground">/{weights[k]}</span>
              </dd>
            </div>
          ))}
        </dl>
      </div>

      <section aria-labelledby="why">
        <Lettering as="h3" className="mb-1">
          <span id="why">Why it fits</span>
        </Lettering>
        {r.excluded_reason ? (
          <p>Excluded from the ranking: {r.excluded_reason}.</p>
        ) : r.reasons.length ? (
          <ul className="flex list-disc flex-col gap-0.5 pl-4 marker:text-faint">
            {r.reasons.map((x) => (
              <li key={x}>{humanize(x)}</li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground">No positive signals were found in the map data.</p>
        )}
        {r.issues.length && r.web_status === "website" ? (
          <>
            <Lettering as="h3" className="mt-3 mb-1">
              Site issues
            </Lettering>
            <ul className="flex list-disc flex-col gap-0.5 pl-4 marker:text-faint">
              {r.issues.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </>
        ) : null}
      </section>

      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <Lettering as="dt" className="pt-0.5">
          Phone
        </Lettering>
        <dd>{r.phone ? r.phone.split(";").map((p) => p.trim()).join(", ") : <span className="text-muted-foreground">None in the map data</span>}</dd>
        <Lettering as="dt" className="pt-0.5">
          Address
        </Lettering>
        <dd>{r.address || <span className="text-muted-foreground">None in the map data</span>}</dd>
        <Lettering as="dt" className="pt-0.5">
          Web
        </Lettering>
        <dd className="min-w-0 truncate">{site ? <Ext href={site}>{host(site) || r.website}</Ext> : <span className="text-muted-foreground">None listed</span>}</dd>
        <Lettering as="dt" className="pt-0.5">
          Verify
        </Lettering>
        <dd className="flex flex-wrap gap-x-3">
          <Ext href={googleSearch(r.name, r.area)}>Google</Ext>
          <Ext href={googleMaps(r.name, null, null)}>Maps</Ext>
          {r.map_link ? <Ext href={r.map_link}>OpenStreetMap</Ext> : null}
        </dd>
      </dl>

      {r.excluded_reason ? null : (
        <div className="flex flex-wrap gap-2">
          {r.status ? null : (
            <Button onClick={() => void setStatus(r.key, "approved", { from: null, name: r.name })} title={STATUS_HELP.approved}>
              Approve
            </Button>
          )}
          {r.status === "rejected" ? (
            <Button variant="outline" onClick={() => void unreject(r.key, r.name)}>
              Undo reject
            </Button>
          ) : (
            <Button variant="outline" onClick={() => void setStatus(r.key, "rejected", { from: r.status || null, name: r.name })} title={STATUS_HELP.rejected}>
              Reject
            </Button>
          )}
          <Link to={`/leads/${r.key}`} className={buttonVariants({ variant: "outline" })}>
            Open
            <ArrowUpRightIcon data-icon="inline-end" />
          </Link>
        </div>
      )}
    </div>
  )
}
