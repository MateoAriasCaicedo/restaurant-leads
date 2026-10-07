import { DownloadIcon, FileTextIcon, GlobeIcon, Trash2Icon, UploadIcon } from "lucide-react"
import { useRef, useState, type DragEvent } from "react"
import { toast } from "sonner"
import { mutate } from "swr"

import { JobLog } from "@/components/jobs"
import { Muted, Section } from "@/components/lead/parts"
import { Ext } from "@/components/plan"
import { Palette } from "@/components/lead/research"
import { Button, buttonVariants } from "@/components/ui/button"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { isActive, keys, useJobs } from "@/hooks/use-data"
import { message, send, upload } from "@/lib/api"
import { fileSize } from "@/lib/format"
import type { FileKind, Job, LeadDetail, LeadFile, Meta } from "@/lib/types"
import { cn } from "@/lib/utils"

const GROUPS: { kind: Exclude<FileKind, "site">; title: string; hint: string; accept: string }[] = [
  { kind: "instagram", title: "Instagram screenshots", hint: "Their grid, a few posts, the bio. Shows how they present themselves.", accept: "image/jpeg,image/png,image/webp" },
  { kind: "maps", title: "Google Maps photos", hint: "The storefront, the room, dishes as customers photograph them.", accept: "image/jpeg,image/png,image/webp" },
  { kind: "menu", title: "Menu", hint: "Photos or screenshots of the menu, or a PDF. Prices are read from these.", accept: "image/jpeg,image/png,image/webp,application/pdf" },
]

/** Plain links: the server answers with Content-Disposition: attachment, so the browser saves instead of navigating. */
function DownloadFile({ file, className }: { file: LeadFile; className?: string }) {
  return (
    <a
      href={`${file.url}?download=1`}
      download={file.name}
      className={cn(buttonVariants({ variant: "secondary", size: "icon-xs" }), className)}
      aria-label={`Download ${file.name}`}
    >
      <DownloadIcon />
    </a>
  )
}

/** A zip of one group (`kind`) or of every group, one folder each. */
function DownloadZip({ lead, kind, label, variant = "outline" }: { lead: LeadDetail; kind?: FileKind; label: string; variant?: "outline" | "ghost" }) {
  return (
    <a
      href={`/api/leads/${lead.key}/files.zip${kind ? `?kind=${kind}` : ""}`}
      download
      className={buttonVariants({ variant, size: "sm" })}
    >
      <DownloadIcon data-icon="inline-start" />
      {label}
    </a>
  )
}

function Dropzone({ lead, kind, title, hint, accept, limit, busyLead }: (typeof GROUPS)[number] & { lead: LeadDetail; limit: number; busyLead: boolean }) {
  const files = lead.files[kind]
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const full = files.length >= limit
  const disabled = busy || busyLead || full

  async function add(list: FileList | File[] | null) {
    const picked = Array.from(list ?? [])
    if (!picked.length) return
    setBusy(true)
    try {
      const res = await upload<{ saved: string[]; errors: string[] }>(`/api/leads/${lead.key}/files/${kind}`, picked)
      for (const e of res.errors) toast.error(e)
      if (res.saved.length) toast.success(`${res.saved.length} ${res.saved.length === 1 ? "file" : "files"} added`)
    } catch (err) {
      toast.error(message(err))
    } finally {
      setBusy(false)
      void mutate(keys.lead(lead.key))
    }
  }

  async function remove(f: LeadFile) {
    try {
      await send("DELETE", f.url)
      toast.success(`${f.name} moved to the lead's .trash folder`)
    } catch (err) {
      toast.error(message(err))
    }
    void mutate(keys.lead(lead.key))
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setOver(false)
    if (!disabled) void add(e.dataTransfer.files)
  }

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-semibold">{title}</h3>
        <span className="figure text-xs text-muted-foreground">
          {files.length} of {limit}
        </span>
      </div>
      <p className="text-[0.8125rem] text-muted-foreground">{hint}</p>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        className={cn("mt-2 border border-dashed border-input p-2", over && !disabled && "border-live bg-live-soft")}
      >
        {files.length ? (
          <ul className="mb-2 grid grid-cols-[repeat(auto-fill,minmax(4rem,1fr))] gap-2">
            {files.map((f) => (
              <li key={f.name} className="group relative border border-border bg-card">
                <a href={f.url} target="_blank" rel="noreferrer" className="block" title={`${f.name} · ${fileSize(f.size)}`}>
                  {f.is_image ? (
                    <img src={`${f.url}?w=320`} alt={f.name} loading="lazy" className="aspect-square w-full object-cover" />
                  ) : (
                    <span className="flex aspect-square flex-col items-center justify-center gap-1 p-2 text-center text-xs break-all">
                      <FileTextIcon className="size-5" aria-hidden="true" />
                      {f.name}
                    </span>
                  )}
                </a>
                <div className="absolute top-1 right-1 flex gap-1 opacity-0 group-focus-within:opacity-100 group-hover:opacity-100">
                  <DownloadFile file={f} />
                  <Button variant="secondary" size="icon-xs" onClick={() => void remove(f)} disabled={busyLead} aria-label={`Remove ${f.name}`}>
                    <Trash2Icon />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
        <input ref={input} type="file" multiple accept={accept} className="sr-only" tabIndex={-1} onChange={(e) => { void add(e.target.files); e.target.value = "" }} />
        <div className="flex flex-wrap items-center gap-2 text-[0.8125rem] text-muted-foreground">
          <Button variant="outline" size="sm" onClick={() => input.current?.click()} disabled={disabled}>
            {busy ? <Spinner data-icon="inline-start" /> : <UploadIcon data-icon="inline-start" />}
            Add files
          </Button>
          {full ? `Full: the analysis reads at most ${limit}. Remove one to add another.` : busyLead ? "Locked while the analysis runs." : "or drop them here"}
          {files.length > 1 ? (
            <span className="ml-auto">
              <DownloadZip lead={lead} kind={kind} label="Download all" variant="ghost" />
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function Notes({ lead }: { lead: LeadDetail }) {
  const [text, setText] = useState(lead.notes_txt)
  const [saving, setSaving] = useState(false)
  const dirty = text !== lead.notes_txt

  async function save() {
    setSaving(true)
    try {
      await send("PUT", `/api/leads/${lead.key}/notes-file`, { text })
      await mutate(keys.lead(lead.key))
      toast.success("Notes saved")
    } catch (err) {
      toast.error(message(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Field>
      <FieldLabel htmlFor="notes-file">Pasted notes for the analysis</FieldLabel>
      <Textarea
        id="notes-file"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={6}
        placeholder="Paste their Instagram bio, a few captions, anything they wrote about themselves."
      />
      <FieldDescription>
        Saved as notes.txt in the lead's folder and read by the analysis (first 6,000 characters). For things only you should see, use the private note on the right.
      </FieldDescription>
      <div>
        <Button size="sm" onClick={save} disabled={!dirty || saving}>
          {saving ? <Spinner data-icon="inline-start" /> : null}
          {dirty ? "Save notes" : "Saved"}
        </Button>
      </div>
    </Field>
  )
}

const SCRAPE_STATUS: Record<string, string> = {
  ok: "Read",
  blocked: "Refused by the site",
  no_match: "Listing is a different restaurant",
  not_found: "Not found",
  no_handle: "No Instagram link known",
  error: "Failed",
}

/** Reads the lead's public Maps listing and Instagram profile in a headless browser, logged out, and saves
 *  what it finds (and a few photos) under the lead. Separate from the research: no Claude, no subscription use. */
function ScrapePanel({ lead, meta, busy }: { lead: LeadDetail; meta?: Meta; busy: boolean }) {
  const { data } = useJobs()
  const [starting, setStarting] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const running = data?.jobs.find((j) => j.kind === "scrape" && j.lead?.key === lead.key && isActive(j))
  const shown = running?.id ?? jobId
  const available = meta?.scrape.available
  const s = lead.scrape

  async function start(sources: string[]) {
    setStarting(sources.join())
    try {
      const res = await send<{ job: Job }>("POST", `/api/leads/${lead.key}/scrape`, { sources })
      setJobId(res.job.id)
      void mutate(keys.jobs)
      void mutate(keys.lead(lead.key))
    } catch (err) {
      toast.error(message(err))
    } finally {
      setStarting(null)
    }
  }

  const row = (label: string, src?: { status: string; note?: string }, detail?: string) =>
    src ? (
      <li className="flex flex-col gap-0.5">
        <span>
          <span className="font-semibold">{label}</span> · {SCRAPE_STATUS[src.status] ?? src.status}
          {detail ? <> · {detail}</> : null}
        </span>
        {src.status !== "ok" && src.note ? <span className="text-muted-foreground">{src.note}</span> : null}
      </li>
    ) : null

  return (
    <Section title="Read their public pages" aside="Google Maps and Instagram, logged out, no key">
      <p className="max-w-2xl text-[0.8125rem] text-muted-foreground">
        A headless browser opens their Maps listing and Instagram profile like an anonymous visitor and saves the rating, reviews, whether Maps flags it closed, and a few photos into the folders above. Both sites forbid scraping in their terms and Instagram usually refuses anonymous visitors; nothing here logs in or gets past a block.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={() => start(["maps", "instagram"])} disabled={!available || busy || !!running || !!starting}>
          {running || starting ? <Spinner data-icon="inline-start" /> : <GlobeIcon data-icon="inline-start" />}
          {running ? "Reading…" : s ? "Read again" : "Read Maps and Instagram"}
        </Button>
        <Button size="sm" variant="outline" onClick={() => start(["maps"])} disabled={!available || busy || !!running || !!starting}>
          Maps only
        </Button>
        <Button size="sm" variant="outline" onClick={() => start(["instagram"])} disabled={!available || busy || !!running || !!starting}>
          Instagram only
        </Button>
        {!available ? <span className="text-[0.8125rem] text-bad">Needs Playwright: pip install playwright, then python -m playwright install chromium.</span> : null}
      </div>
      {shown ? (
        <div className="mt-3">
          <JobLog id={shown} />
        </div>
      ) : null}
      {s && !running ? (
        <div className="mt-4 max-w-2xl">
          <p className="mb-2 text-[0.8125rem] text-muted-foreground">Last read {new Date(s.scraped_at).toLocaleString()}</p>
          <ul className="flex flex-col gap-2 text-[0.8125rem]">
            {row("Google Maps", s.maps, [s.maps?.rating ? `${s.maps.rating}★` : null, s.maps?.review_count ? `${s.maps.review_count} reviews` : null, s.maps?.closed_flag].filter(Boolean).join(" · "))}
            {row("Instagram", s.instagram, [s.instagram?.handle ? `@${s.instagram.handle}` : null, s.instagram?.followers != null ? `${s.instagram.followers} followers` : null, s.instagram?.last_post ? `last post ${s.instagram.last_post}` : null].filter(Boolean).join(" · "))}
          </ul>
          {s.maps?.status === "ok" && s.maps.reviews?.length ? (
            <ul className="mt-3 flex flex-col gap-1 border-l-2 border-rule pl-3 text-[0.8125rem]">
              {s.maps.reviews.slice(0, 4).map((r, i) => (
                <li key={i}>
                  <span className="text-muted-foreground">
                    {r.stars ?? "?"}★ · {r.when}
                  </span>{" "}
                  {(r.text ?? "").slice(0, 220)}
                </li>
              ))}
            </ul>
          ) : null}
          {s.maps?.url ? (
            <p className="mt-2">
              <Ext href={s.maps.url}>Open the Maps listing</Ext>
            </p>
          ) : null}
        </div>
      ) : null}
    </Section>
  )
}

export function MaterialsTab({ lead, meta, busy }: { lead: LeadDetail; meta?: Meta; busy: boolean }) {
  const site = lead.files.site
  const total = Object.values(lead.files).reduce((n, list) => n + list.length, 0)
  return (
    <>
      <Section title="What the analysis reads" aside="Add what you want it to see, or read their public pages below">
        <div className="grid gap-6 lg:grid-cols-3">
          {GROUPS.map((g) => (
            <Dropzone key={g.kind} lead={lead} {...g} limit={g.kind === "menu" ? 12 : (meta?.limits.photos_per_source ?? 10)} busyLead={busy} />
          ))}
        </div>
        {total > 1 ? (
          <div className="mt-4 flex flex-wrap items-center gap-3 text-[0.8125rem] text-muted-foreground">
            <DownloadZip lead={lead} label="Download everything" />
            Every photo, screenshot and menu file above plus the photos from their site, as one zip.
          </div>
        ) : null}
        <div className="mt-6 max-w-2xl">
          <Notes key={lead.notes_txt} lead={lead} />
        </div>
      </Section>

      <ScrapePanel lead={lead} meta={meta} busy={busy} />

      <Section title="Collected from their own site" aside={lead.site?.url ?? undefined}>
        {lead.site ? (
          <>
            {lead.site.error ? <p className="text-bad">The site could not be crawled: {lead.site.error}.</p> : null}
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <h3 className="mb-1 font-semibold">Colours and fonts in their CSS</h3>
                <Palette items={lead.site.palette} />
                <p className="mt-2">{lead.site.fonts.length ? lead.site.fonts.join(", ") : <Muted>No custom fonts found.</Muted>}</p>
              </div>
              <div>
                <h3 className="mb-1 font-semibold">Pages read</h3>
                <ul className="flex flex-col gap-0.5 text-[0.8125rem]">
                  {lead.site.pages.map((p) => (
                    <li key={p} className="truncate">
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            {site.length ? (
              <>
                <ul className="mt-4 grid grid-cols-4 gap-2 sm:grid-cols-6">
                  {site.map((f) => (
                    <li key={f.name} className="group relative">
                      <a href={f.url} target="_blank" rel="noreferrer" className="block border border-border">
                        <img src={`${f.url}?w=320`} alt="Photo from their site" loading="lazy" className="aspect-square w-full object-cover" />
                      </a>
                      <DownloadFile file={f} className="absolute top-1 right-1 opacity-0 group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100" />
                    </li>
                  ))}
                </ul>
                {site.length > 1 ? (
                  <div className="mt-2">
                    <DownloadZip lead={lead} kind="site" label="Download site photos" />
                  </div>
                ) : null}
              </>
            ) : null}
          </>
        ) : (
          <p className="prose-measure text-muted-foreground">
            Nothing yet. If the restaurant has a working website, its pages, menu files, colours and photos are collected when you run the analysis.
          </p>
        )}
        {lead.has_context ? (
          <p className="mt-3">
            <a href={`/api/leads/${lead.key}/context.md`} target="_blank" rel="noreferrer" className="underline decoration-border hover:decoration-foreground">
              View everything collected for the analysis (context.md)
            </a>
          </p>
        ) : null}
      </Section>
    </>
  )
}
