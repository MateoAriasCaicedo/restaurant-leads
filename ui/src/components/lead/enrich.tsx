import { PaletteIcon, ScanSearchIcon, XIcon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"
import { mutate } from "swr"

import { JobLog } from "@/components/jobs"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Popover, PopoverContent, PopoverDescription, PopoverHeader, PopoverTitle, PopoverTrigger } from "@/components/ui/popover"
import { Spinner } from "@/components/ui/spinner"
import { isActive, keys, useJobLog, useJobs } from "@/hooks/use-data"
import { message, send } from "@/lib/api"
import type { Job, LeadDetail, Meta } from "@/lib/types"

/** Starts the researched analysis of this one lead. It spends subscription usage and takes minutes, so it
 *  is always a deliberate second click, never a default action. */
export function EnrichButton({ lead, meta, onStarted }: { lead: LeadDetail; meta?: Meta; onStarted: (job: Job) => void }) {
  const { data: jobs } = useJobs()
  const [open, setOpen] = useState(false)
  const [starting, setStarting] = useState(false)
  const [scrape, setScrape] = useState(false)
  const running = jobs?.jobs.find((j) => j.kind === "enrich" && isActive(j))
  const here = running?.lead?.key === lead.key
  const photos = lead.files.instagram.length + lead.files.maps.length
  const blocked = !meta?.claude?.available
    ? "The Claude Code CLI was not found on this machine, so research cannot run."
    : running && !here
      ? `An analysis of ${running.lead?.name ?? "another lead"} is running. Leads are researched one at a time.`
      : null

  async function start() {
    setStarting(true)
    try {
      const res = await send<{ job: Job }>("POST", `/api/leads/${lead.key}/enrich`, { scrape })
      setOpen(false)
      onStarted(res.job)
      void mutate(keys.jobs)
      void mutate(keys.lead(lead.key))
    } catch (err) {
      toast.error(message(err))
    } finally {
      setStarting(false)
    }
  }

  if (here) {
    return (
      <Button disabled>
        <Spinner data-icon="inline-start" />
        {running?.params.mode === "design" ? "Writing design system" : "Researching"}
      </Button>
    )
  }
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<Button variant={lead.profile ? "outline" : "default"} />}>
        <ScanSearchIcon data-icon="inline-start" />
        {lead.profile ? "Research again" : "Get insights"}
      </PopoverTrigger>
      <PopoverContent align="end" className="w-88 gap-3 p-4">
        <PopoverHeader>
          <PopoverTitle>Research {lead.place.name}</PopoverTitle>
          <PopoverDescription>
            Claude reads what has been collected, looks at the photos and menu files, and searches the web for reviews, social pages and signs that it is open. It writes the profile, menu and presence.
          </PopoverDescription>
        </PopoverHeader>
        <ul className="flex list-disc flex-col gap-1 pl-4 text-[0.8125rem] marker:text-faint">
          <li>Takes several minutes and uses your Claude subscription.</li>
          <li>{lead.status ? "Keeps the current status until the research is saved." : "Marks the lead approved, then enriched when the research is saved."}</li>
          {lead.profile ? <li>Replaces the current profile. The previous one is kept in the job's folder.</li> : null}
          {photos === 0 ? <li>No Instagram or Maps screenshots yet: add some under Materials first for a better read of how they look.</li> : null}
        </ul>
        <label className="flex items-start gap-2 text-[0.8125rem]">
          <Checkbox checked={scrape} onCheckedChange={(v) => setScrape(v === true)} disabled={!meta?.scrape?.available} className="mt-0.5" />
          <span>
            Also read its public Google Maps and Instagram pages
            <span className="block text-muted-foreground">
              {meta?.scrape?.available
                ? "No login or key: a headless browser reads the listing, reviews and a few photos. Instagram often refuses logged-out visitors, and both sites forbid scraping in their terms."
                : "Needs Playwright: pip install playwright, then python -m playwright install chromium."}
            </span>
          </span>
        </label>
        {blocked ? <p className="text-[0.8125rem] text-bad">{blocked}</p> : null}
        <div className="flex gap-2">
          <Button onClick={start} disabled={!!blocked || starting}>
            {starting ? <Spinner data-icon="inline-start" /> : null}
            Start research
          </Button>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Not now
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}

/** Writes only the design system of a lead that is already researched. Like research it spends subscription usage
 *  and takes minutes, so it is a deliberate second click. */
export function DesignSystemButton({ lead, meta, onStarted, again }: { lead: LeadDetail; meta?: Meta; onStarted: (job: Job) => void; again?: boolean }) {
  const { data: jobs } = useJobs()
  const [open, setOpen] = useState(false)
  const [starting, setStarting] = useState(false)
  const running = jobs?.jobs.find((j) => j.kind === "enrich" && isActive(j))
  const here = running?.lead?.key === lead.key
  const blocked = !meta?.claude?.available
    ? "The Claude Code CLI was not found on this machine, so this cannot run."
    : running && !here
      ? `An analysis of ${running.lead?.name ?? "another lead"} is running. Leads are analyzed one at a time.`
      : null

  async function start() {
    setStarting(true)
    try {
      const res = await send<{ job: Job }>("POST", `/api/leads/${lead.key}/design-system`, {})
      setOpen(false)
      onStarted(res.job)
      void mutate(keys.jobs)
      void mutate(keys.lead(lead.key))
    } catch (err) {
      toast.error(message(err))
    } finally {
      setStarting(false)
    }
  }

  if (here) {
    return (
      <Button disabled size={again ? "sm" : "default"}>
        <Spinner data-icon="inline-start" />
        {running?.params.mode === "design" ? "Writing" : "Researching"}
      </Button>
    )
  }
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<Button variant={again ? "outline" : "default"} size={again ? "sm" : "default"} className={again ? "text-foreground" : undefined} />}>
        <PaletteIcon data-icon="inline-start" />
        {again ? "Write again" : "Write design system"}
      </PopoverTrigger>
      <PopoverContent align="end" className="w-88 gap-3 p-4">
        <PopoverHeader>
          <PopoverTitle>Design system for {lead.place.name}</PopoverTitle>
          <PopoverDescription>
            Claude reads the profile, menu and photos already collected and writes the colours, type, spacing and components for a Next.js and Tailwind site.
          </PopoverDescription>
        </PopoverHeader>
        <ul className="flex list-disc flex-col gap-1 pl-4 text-[0.8125rem] marker:text-faint">
          <li>No new web research. Takes a few minutes and uses your Claude subscription.</li>
          <li>Changes only the design system: the profile, build plan and menu stay as they are.</li>
          {again ? <li>Replaces the current design system. The previous one is kept in the job's folder.</li> : null}
        </ul>
        {blocked ? <p className="text-[0.8125rem] text-bad">{blocked}</p> : null}
        <div className="flex gap-2">
          <Button onClick={start} disabled={!!blocked || starting}>
            {starting ? <Spinner data-icon="inline-start" /> : null}
            Start
          </Button>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Not now
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}

/** The running (or just finished) analysis, shown in place on the lead page. */
export function EnrichProgress({ jobId, onDismiss }: { jobId: string; onDismiss: () => void }) {
  const state = useJobLog(jobId)
  const job = state?.job
  const done = job && !isActive(job)
  const design = job?.params.mode === "design"
  const noun = design ? "Design system" : "Research"
  return (
    <section aria-label={`${noun} progress`} className="mb-6 border border-live bg-card p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">
            {!job ? noun : job.status === "succeeded" ? `${noun} finished` : done ? `${noun} stopped` : design ? "Writing the design system" : "Researching this lead"}
          </h2>
          <p className="text-[0.8125rem] text-muted-foreground">
            {!job || !done
              ? "You can leave this page; the job keeps running and appears under Jobs."
              : job.status === "succeeded"
                ? design
                  ? "The design system is on its tab."
                  : job.params.dry_run
                    ? "Dry run: the result was checked but not saved."
                    : "The profile, menu and presence below are new."
                : "Nothing was changed on the lead."}
          </p>
        </div>
        {done ? (
          <Button variant="ghost" size="icon-sm" onClick={onDismiss} aria-label="Dismiss">
            <XIcon />
          </Button>
        ) : null}
      </div>
      <JobLog id={jobId} />
    </section>
  )
}
