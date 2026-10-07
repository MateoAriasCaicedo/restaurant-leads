// Shapes returned by the local API (server/). Analysis objects (profile, menu, presence) are written by a
// model, so every field in them is optional here and rendered defensively.

export type Tier = "A" | "B" | "C"
export type Status = "approved" | "enriched" | "ready" | "contacted" | "rejected"
export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled" | "interrupted"

export interface ReachFlags {
  phone: boolean
  whatsapp: boolean
  email: boolean
  social: boolean
}

export interface LastContact {
  at: number
  channel: string
  outcome: string
  count: number
}

export interface LeadRow {
  key: string
  place_id: string
  tier: Tier
  sell_score: number
  name: string
  area: string
  phone: string | null
  address: string | null
  rating: number | null
  reviews: number | null
  price: string
  web_status: "none" | "social_only" | "website" | "unknown"
  web_score: number | ""
  website: string
  url_status: "" | "ok" | "parked" | "blocked" | "dead" | "unreachable"
  url_note: string
  need: number
  ability: number
  momentum: number
  reach: number
  map_link: string | null
  status: Status | ""
  operating_status: string
  reasons: string[]
  issues: string[]
  audited: boolean
  cuisine: string
  quality: number
  quality_tier: "premium" | "candidate" | ""
  quality_source: "maps" | "osm"
  quality_reasons: string[]
  reach_flags: ReachFlags
  has_profile: boolean
  last_contact: LastContact | null
  excluded_reason?: string
}

export interface LeadList {
  rows: LeadRow[]
  hidden: LeadRow[]
  skipped: Record<string, number>
  counts: { places: number; scored: number; audited: number; profiled: number; tiers: Record<Tier, number>; premium: number; candidates: number }
}

export interface Area {
  key: string
  lat: number
  lng: number
  radius_m: number
  default: boolean
  places: number
  audited: number
  fetched_at: number | null
}

export interface Meta {
  app_name: string
  statuses: Status[]
  channels: string[]
  outcomes: string[]
  areas: Area[]
  unaudited: number
  weights: Record<Component, number>
  tiers: { osm: { a: number; b: number }; rich: { a: number; b: number } }
  limits: { photos_per_source: number; upload_mb: number; url_recheck_days: number; competitor_radius_m: number }
  scrape: { available: boolean }
  maps_verified: number
  claude: { available: boolean; version: string | null; model: string }
}

export type Component = "need" | "ability" | "momentum" | "reach"

export interface Audit {
  web_type: "none" | "social_only" | "website"
  final_url: string | null
  http_ok: number | null
  https: number | null
  viewport: number | null
  has_title: number | null
  has_meta_desc: number | null
  has_h1: number | null
  has_menu_text: number | null
  menu_pdf_only: number | null
  has_whatsapp: number | null
  has_tel: number | null
  has_reserve: number | null
  has_order: number | null
  has_schema: number | null
  cheap_builder: number | null
  copyright_year: number | null
  page_kb: number | null
  mobile_perf: number | null
  web_score: number
  issues: string[]
  audited_at: number
}

export interface UrlCheck {
  url: string
  status: "ok" | "parked" | "blocked" | "dead" | "unreachable"
  http_code: number | null
  final_url: string | null
  note: string | null
  name_match: number | null
  checked_at: number
}

export interface Score {
  total: number
  tier: Tier
  need: number
  ability: number
  momentum: number
  reach: number
  reasons: string[]
  weights: Record<Component, number>
  rich: boolean
  tier_a: number
  tier_b: number
}

export interface LeadFile {
  name: string
  size: number
  url: string
  mtime: number
  is_image: boolean
}

export type FileKind = "instagram" | "maps" | "menu" | "site"

export interface Contact {
  id: number
  at: number
  channel: string
  outcome: string
  note: string
  created_at: number
}

export interface BlockPoint {
  key: string
  name: string
  dx: number
  dy: number
  distance_m: number
  web: "working" | "broken" | "blocked" | "social_only" | "none" | "unknown"
  cuisine: string
  same_cuisine: boolean
  chain: boolean
}

export interface Competitors {
  radius_m: number
  note?: string
  restaurants_nearby?: number
  with_working_website?: number
  without_working_website?: number
  lead_cuisine?: string | null
  same_cuisine_nearby?: number
  same_cuisine_with_working_website?: number
  nearest?: { name: string; distance_m: number; cuisine: string | null; web: string; web_score: number | null }[]
  insight?: string
}

type Strs = string[] | undefined

export interface DevDirection {
  summary?: string
  deliverables?: Strs
  goals?: Strs
  pages?: { name?: string; purpose?: string; key_content?: Strs }[]
  features?: { name?: string; detail?: string; priority?: "must" | "should" | "later" }[]
  menu_system?: string
  tech_stack?: { layer?: string; choice?: string; why?: string }[]
  seo_plan?: { target_keywords?: Strs; on_page?: Strs; local?: Strs; structured_data?: Strs }
  integrations?: Strs
  content_needed?: Strs
  domain_and_hosting?: string
  phases?: { name?: string; size?: "S" | "M" | "L"; tasks?: Strs }[]
  risks?: Strs
  outreach?: {
    channels?: Strs
    timing?: string
    talking_points?: Strs
    objections?: { objection?: string; response?: string }[]
    compliance?: string
  }
  next_steps?: Strs
}

/** profile/design_system.json: the visual system for the lead's site. Model-written, so every field may be missing or the wrong type. */
export interface DesignSystem {
  concept?: string
  principles?: Strs
  colors?: { name?: string; hex?: string; role?: string; usage?: string }[]
  fonts?: { role?: string; family?: string; kind?: string; weights?: number[]; why?: string }[]
  type_scale?: { token?: string; size?: string; line_height?: string; weight?: number; usage?: string }[]
  spacing?: { scale?: Strs; max_width?: string; layout?: string }
  shape?: { radius?: string; borders?: string; shadows?: string }
  imagery?: { treatment?: string; aspect_ratios?: Strs; guidelines?: Strs }
  components?: { name?: string; description?: string; classes?: { part?: string; classes?: string }[]; states?: Strs; used_on?: Strs }[]
  motion?: string
  accessibility?: Strs
  microcopy?: { context?: string; text?: string }[]
  dos?: Strs
  donts?: Strs
  basis?: string
}

export type Verdict = "active" | "uncertain" | "likely_closed" | "closed" | "unknown"
export type Level = "high" | "medium" | "low"

export interface Profile {
  identity?: { cuisine?: Strs; specialties?: Strs; price_tier?: string; audience?: string; positioning?: string }
  visual_identity?: { vibe?: string; palette?: Strs; typography?: string; photo_style?: string }
  tone_of_voice?: string
  menu_summary?: string
  operating_status?: { verdict?: Verdict; confidence?: Level; reasoning?: string }
  reputation?: { summary?: string; ratings_overview?: string; praise?: Strs; complaints?: Strs }
  online_activity?: string
  competitive_landscape?: string
  web_gaps?: Strs
  design_direction?: {
    site_structure?: Strs
    menu_experience?: string
    palette_suggestion?: string
    typography_suggestion?: string
  }
  development_direction?: DevDirection
  pitch_hooks?: Strs
  confidence?: { field?: string; level?: Level; source?: string; note?: string }[]
}

export interface Menu {
  sections?: { name?: string; items?: { name?: string; description?: string; price_cop?: number | null }[] }[]
  notes?: string
}

export interface Presence {
  platforms?: {
    platform?: string
    found?: boolean
    url?: string
    handle?: string
    rating?: number | null
    review_count?: number | null
    followers?: number | null
    last_activity?: string
    notes?: string
  }[]
  review_themes?: { praise?: Strs; complaints?: Strs; sample_quotes?: Strs; recent_review_activity?: string }
  instagram?: {
    handle?: string
    followers?: number | null
    posting_frequency?: string
    last_post?: string
    content_style?: string
  }
  operating_signals?: {
    signal?: string
    direction?: "open" | "closed" | "unclear"
    evidence?: string
    source_url?: string
    date?: string
  }[]
  verdict?: { status?: Verdict; confidence?: Level; reasoning?: string }
  recognition?: Strs
  promotions_or_events?: Strs
  identity_check?: string
  caveats?: Strs
  sources?: { url?: string; title?: string }[]
}

export interface JobStep {
  name: string
  label: string
  status: "pending" | "running" | "done" | "failed" | "cancelled"
  started?: number
  ended?: number
}

export interface Job {
  id: string
  kind: "discover" | "audit" | "audit_one" | "scrape" | "enrich" | "quality" | "find_sites" | "pagespeed" | "rescore" | "backfill"
  title: string
  lane: "pipeline" | "enrich"
  params: Record<string, unknown>
  lead: { key: string; name: string } | null
  status: JobStatus
  steps: JobStep[]
  step: string | null
  error: string | null
  result: { files?: string[]; draft_dir?: string }
  created: number
  started: number | null
  ended: number | null
  line_count: number
}

export interface JobLine {
  seq: number
  t: number | null
  step: string | null
  level: "info" | "note" | "warn" | "error"
  text: string
}

export interface LeadDetail {
  key: string
  slug: string
  place: {
    place_id: string
    area: string
    name: string
    address: string | null
    lat: number | null
    lng: number | null
    rating: number | null
    review_count: number | null
    price_level: string | null
    website: string | null
    phone: string | null
    maps_url: string | null
    has_hours: number | null
    fetched_at: number | null
  }
  tags: Record<string, string>
  excluded_reason: string | null
  audit: Audit | null
  url_check: UrlCheck | null
  score: Score
  reach_flags: ReachFlags
  status: Status | null
  profile: Profile | null
  profile_meta: { created_at: number; models: Record<string, string> | null } | null
  profile_problems: Record<string, string[]> | null
  menu: Menu | null
  presence: Presence | null
  design_system: DesignSystem | null
  competitors: Competitors
  block: { radius_m: number; points: BlockPoint[] | null }
  site: { url?: string; error?: string; palette: string[]; fonts: string[]; pages: string[] } | null
  scrape: Scrape | null
  files: Record<FileKind, LeadFile[]>
  notes_txt: string
  has_context: boolean
  private_note: { body: string; updated_at: number | null }
  contacts: Contact[]
  active_job: Job | null
}

/** profile/scrape.json: the logged-out read of the lead's Google Maps listing and Instagram profile. */
export interface Scrape {
  scraped_at: string
  maps?: {
    status: string
    note?: string
    name?: string
    rating?: number | null
    review_count?: number | null
    category?: string | null
    address?: string | null
    phone?: string | null
    closed_flag?: string | null
    url?: string
    reviews?: { stars: number | null; when: string | null; text: string | null }[]
    photos?: string[]
  }
  instagram?: {
    status: string
    note?: string
    handle?: string
    followers?: number | null
    post_count?: number | null
    last_post?: string | null
    bio?: string | null
    url?: string
    photos?: string[]
  }
}
