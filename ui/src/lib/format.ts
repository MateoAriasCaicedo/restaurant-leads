import type { Audit, LeadRow, UrlCheck } from "./types"

/** Profile, menu and presence text is written by a model from public web content. Only http(s) links are
 *  ever made clickable. */
export function safeHref(url: unknown): string | null {
  if (typeof url !== "string") return null
  try {
    const u = new URL(url.trim())
    return u.protocol === "http:" || u.protocol === "https:" ? u.href : null
  } catch {
    return null
  }
}

/** OSM website tags often lack a scheme. */
export function withScheme(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `http://${url.replace(/^\/+/, "")}`
}

export function host(url: string | null | undefined): string {
  const href = safeHref(url ? withScheme(url) : "")
  return href ? new URL(href).host.replace(/^www\./, "") : ""
}

/** osm:node/5546129027 -> "N 5546129027": the plot's reference on the source map. */
export function plotNo(placeId: string): string {
  const m = /^osm:(\w)\w*\/(\d+)$/.exec(placeId)
  return m ? `${m[1].toUpperCase()} ${m[2]}` : placeId
}

const collator = new Intl.Collator("es", { sensitivity: "base" })
export function norm(s: string): string {
  return s.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
}
export const compareText = collator.compare

export function cop(n: number | null | undefined): string {
  return typeof n === "number" ? `$${Math.round(n).toLocaleString("es-CO")}` : ""
}

const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" })
const timeFmt = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" })

export function date(ts: number | null | undefined): string {
  return ts ? dateFmt.format(ts * 1000) : ""
}

export function dateTime(ts: number | null | undefined): string {
  return ts ? `${dateFmt.format(ts * 1000)}, ${timeFmt.format(ts * 1000)}` : ""
}

export function ago(ts: number | null | undefined): string {
  if (!ts) return ""
  const s = Date.now() / 1000 - ts
  if (s < 90) return "just now"
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  const d = Math.round(s / 86400)
  return d === 1 ? "yesterday" : d < 45 ? `${d} days ago` : date(ts)
}

export function duration(from: number | null, to: number | null): string {
  if (!from) return ""
  const s = Math.max(0, Math.round((to ?? Date.now() / 1000) - from))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`
}

export function fileSize(bytes: number): string {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function label(s: string): string {
  if (s === "whatsapp") return "WhatsApp"
  if (s === "ok") return "OK"
  const t = s.replace(/_/g, " ")
  return t.charAt(0).toUpperCase() + t.slice(1)
}

/** Map-data values use underscores (steak_house, coffee_shop): show them as words. */
export function humanize(s: string): string {
  return s.replace(/_/g, " ").replace(/;/g, ", ")
}

const AREA_NAMES: Record<string, string> = { guatape: "Guatapé" }
/** An area key from config.ALL_AREAS as a place name: la_ceja -> La Ceja. */
export function areaName(key: string): string {
  return AREA_NAMES[key] ?? key.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")
}

export type WebKind = "vacant" | "social" | "built" | "broken" | "blocked" | "unknown"

/** What stands on the plot, in plan terms. */
export function webState(
  src: Pick<LeadRow, "web_status" | "url_status" | "web_score" | "audited"> | { audit: Audit | null; url_check: UrlCheck | null },
): { kind: WebKind; text: string; detail: string } {
  let type: string, url: string, score: number | "", audited: boolean
  if ("audit" in src) {
    type = src.audit?.web_type ?? "unknown"
    url = src.url_check?.status ?? ""
    score = src.audit?.web_score ?? ""
    audited = !!src.audit
  } else {
    type = src.web_status
    url = src.url_status
    score = src.web_score
    audited = src.audited
  }
  if (!audited) return { kind: "unknown", text: "Not audited", detail: "Run the audit to check for a website." }
  if (url === "blocked") return { kind: "blocked", text: "Site blocks checks", detail: "The site refused the automated check. Open it yourself." }
  if (url && url !== "ok") return { kind: "broken", text: `Link ${url}`, detail: "The listed website does not work: as good as no website." }
  if (type === "website") return { kind: "built", text: `Site ${score}/100`, detail: "A working website. The score is its quality, higher is better." }
  if (type === "social_only") return { kind: "social", text: "Social page only", detail: "Only an Instagram, Facebook or delivery page is listed." }
  return { kind: "vacant", text: "No website", detail: "No website on the map data. Verify with a quick search: it can be a data gap." }
}

export function googleSearch(name: string, area: string): string {
  return `https://www.google.com/search?q=${encodeURIComponent(`${name} ${area} Medellín restaurante`)}`
}

export function googleMaps(name: string, lat: number | null, lng: number | null): string {
  const q = encodeURIComponent(`${name} Medellín`)
  return lat != null && lng != null
    ? `https://www.google.com/maps/search/${q}/@${lat},${lng},18z`
    : `https://www.google.com/maps/search/${q}`
}
