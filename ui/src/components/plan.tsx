// The plan's own marks: tier zones, the parcel strip, what stands on a plot, reach, status stamps.
import { AtSignIcon, MailIcon, MessageCircleIcon, PhoneIcon } from "lucide-react"
import type { ReactNode } from "react"

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { label, safeHref, type WebKind } from "@/lib/format"
import type { Component, ReachFlags, Status, Tier } from "@/lib/types"
import { cn } from "@/lib/utils"

const HATCH = "repeating-linear-gradient(135deg, var(--zone-c) 0 1.5px, transparent 1.5px 4px)"
const ZONE_BG: Record<Tier, string> = { A: "var(--zone-a)", B: "var(--zone-b)", C: "var(--zone-c)" }

export function TierZone({ tier, className }: { tier: Tier; className?: string }) {
  return (
    <span
      className={cn(
        "lettering inline-grid size-5 shrink-0 place-items-center border border-rule",
        tier === "A" && "bg-zone-a text-white",
        tier === "B" && "bg-zone-b text-zone-b-ink",
        className,
      )}
      style={tier === "C" ? { backgroundImage: HATCH } : undefined}
      aria-label={`Tier ${tier}`}
    >
      {tier === "C" ? <span className="bg-background px-[2px] leading-3">C</span> : tier}
    </span>
  )
}

const LOTS: { key: Component; name: string }[] = [
  { key: "need", name: "Need" },
  { key: "ability", name: "Ability" },
  { key: "momentum", name: "Momentum" },
  { key: "reach", name: "Reach" },
]

/** The score drawn as a parcel: one lot per component, as wide as its weight, filled to what was earned. */
export function ParcelStrip({
  values,
  weights,
  tier,
  size = "sm",
  className,
}: {
  values: Record<Component, number>
  weights: Record<Component, number>
  tier: Tier
  size?: "sm" | "lg"
  className?: string
}) {
  const text = LOTS.map((l) => `${l.name} ${values[l.key]}/${weights[l.key]}`).join(", ")
  return (
    <div
      role="img"
      aria-label={text}
      className={cn("flex border border-rule bg-background", size === "sm" ? "h-3 w-24" : "h-7 w-full", className)}
    >
      {LOTS.map((l, i) => {
        const pct = Math.max(0, Math.min(100, (values[l.key] / weights[l.key]) * 100))
        return (
          <div
            key={l.key}
            className={cn("relative h-full", i > 0 && "border-l border-rule")}
            style={{ flexGrow: weights[l.key], flexBasis: 0 }}
          >
            <div
              className="h-full"
              style={{
                width: `${pct}%`,
                background: ZONE_BG[tier],
                backgroundImage:
                  size === "lg"
                    ? "repeating-linear-gradient(135deg, rgb(21 32 29 / 0.28) 0 1px, transparent 1px 5px)"
                    : undefined,
              }}
            />
          </div>
        )
      })}
    </div>
  )
}

/** What stands on the plot: vacant (no website), a social page, a built site, a broken or blocked link. */
export function WebGlyph({ kind, className }: { kind: WebKind; className?: string }) {
  const stroke = "var(--ink)"
  return (
    <svg viewBox="0 0 12 12" className={cn("size-3 shrink-0", className)} aria-hidden="true">
      {kind === "built" && <rect x="0.5" y="0.5" width="11" height="11" fill="var(--good)" stroke="var(--good)" />}
      {kind === "vacant" && <rect x="0.5" y="0.5" width="11" height="11" fill="none" stroke={stroke} strokeDasharray="2 1.5" />}
      {kind === "social" && (
        <>
          <rect x="0.5" y="0.5" width="11" height="11" fill="none" stroke={stroke} />
          <path d="M0.5 6 6 0.5M0.5 11.5 11.5 0.5M6 11.5 11.5 6" stroke={stroke} fill="none" />
        </>
      )}
      {kind === "broken" && (
        <>
          <rect x="0.5" y="0.5" width="11" height="11" fill="none" stroke={stroke} />
          <path d="M3 3l6 6M9 3l-6 6" stroke={stroke} fill="none" />
        </>
      )}
      {kind === "blocked" && (
        <>
          <rect x="0.5" y="0.5" width="11" height="11" fill="none" stroke={stroke} />
          <path d="M3 6h6" stroke={stroke} strokeWidth="1.5" fill="none" />
        </>
      )}
      {kind === "unknown" && <rect x="0.5" y="0.5" width="11" height="11" fill="none" stroke="var(--faint)" strokeDasharray="1 1.5" />}
    </svg>
  )
}

export function WebState({ state }: { state: { kind: WebKind; text: string; detail: string } }) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span
            className={cn(
              "inline-flex items-center gap-1.5 whitespace-nowrap",
              state.kind === "unknown" && "text-muted-foreground",
            )}
          />
        }
      >
        <WebGlyph kind={state.kind} />
        {state.text}
      </TooltipTrigger>
      <TooltipContent>{state.detail}</TooltipContent>
    </Tooltip>
  )
}

const REACH: { key: keyof ReachFlags; icon: typeof PhoneIcon; yes: string; no: string }[] = [
  { key: "phone", icon: PhoneIcon, yes: "Public phone", no: "No phone in the map data" },
  { key: "whatsapp", icon: MessageCircleIcon, yes: "WhatsApp listed", no: "No WhatsApp listed" },
  { key: "email", icon: MailIcon, yes: "Public email", no: "No email listed" },
  { key: "social", icon: AtSignIcon, yes: "Instagram or Facebook listed", no: "No social page listed" },
]

/** Ways to reach the restaurant. Missing ones stay visible as faint marks, so a gap reads as a gap. */
export function Reach({ flags }: { flags: ReachFlags }) {
  const have = REACH.filter((r) => flags[r.key]).map((r) => r.yes)
  return (
    <span className="inline-flex items-center gap-1" role="img" aria-label={have.length ? have.join(", ") : "No way to reach them listed"}>
      {REACH.map((r) => (
        <Tooltip key={r.key}>
          <TooltipTrigger render={<span className={cn("inline-flex", flags[r.key] ? "text-foreground" : "text-faint")} />}>
            <r.icon className="size-3.5" strokeWidth={flags[r.key] ? 2 : 1.5} aria-hidden="true" />
          </TooltipTrigger>
          <TooltipContent>{flags[r.key] ? r.yes : r.no}</TooltipContent>
        </Tooltip>
      ))}
    </span>
  )
}

const STATUS_STYLE: Record<Status, string> = {
  approved: "border-rule text-foreground",
  enriched: "border-rule bg-foreground text-background",
  ready: "border-good bg-good text-white",
  contacted: "border-good text-good",
  rejected: "border-border text-muted-foreground line-through",
}

export const STATUS_HELP: Record<Status, string> = {
  approved: "Chosen for research",
  enriched: "Researched: profile exists",
  ready: "Reviewed and ready to contact",
  contacted: "Contacted at least once",
  rejected: "Not a fit, or asked not to be contacted",
}

export function StatusStamp({ status, className }: { status: Status | "" | null; className?: string }) {
  if (!status) return null
  return <span className={cn("lettering inline-flex h-5 items-center border px-1.5", STATUS_STYLE[status], className)}>{status}</span>
}

const VERDICT_STYLE: Record<string, string> = {
  active: "bg-good-soft text-good",
  uncertain: "bg-warn-soft text-warn",
  likely_closed: "bg-bad-soft text-bad",
  closed: "bg-bad-soft text-bad",
  unknown: "bg-muted text-muted-foreground",
}

export function VerdictMark({ verdict, className }: { verdict: string | null | undefined; className?: string }) {
  if (!verdict) return null
  return (
    <span className={cn("lettering inline-flex h-5 items-center px-1.5", VERDICT_STYLE[verdict] ?? VERDICT_STYLE.unknown, className)}>
      {label(verdict)}
    </span>
  )
}

export function Mark({ tone = "muted", children, className }: { tone?: "good" | "warn" | "bad" | "muted" | "live" | "ink" | "outline"; children: ReactNode; className?: string }) {
  const tones = {
    good: "bg-good-soft text-good",
    warn: "bg-warn-soft text-warn",
    bad: "bg-bad-soft text-bad",
    muted: "bg-muted text-muted-foreground",
    live: "bg-live-soft text-accent-foreground",
    ink: "bg-foreground text-background",
    outline: "border border-rule text-foreground",
  }
  return <span className={cn("lettering inline-flex h-5 items-center px-1.5", tones[tone], className)}>{children}</span>
}

/** A link to somewhere outside the app. Text from analysis is only ever linked when it is http(s). */
export function Ext({ href, children, className }: { href: string | null | undefined; children?: ReactNode; className?: string }) {
  const safe = safeHref(href)
  if (!safe) return <span className={className}>{children ?? href}</span>
  return (
    <a href={safe} target="_blank" rel="noopener noreferrer" className={cn("underline decoration-border hover:decoration-foreground", className)}>
      {children ?? safe}
    </a>
  )
}

export function Lettering({ children, className, as: Tag = "span" }: { children: ReactNode; className?: string; as?: "span" | "div" | "h2" | "h3" | "dt" | "th" }) {
  return <Tag className={cn("lettering text-muted-foreground", className)}>{children}</Tag>
}
