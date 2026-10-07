import { useState } from "react"

import { JobStatusMark, useJobsDrawer } from "@/components/jobs"
import { Section } from "@/components/lead/parts"
import { Lettering } from "@/components/plan"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverDescription, PopoverHeader, PopoverTitle, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { isActive, useJobs, useMeta } from "@/hooks/use-data"
import { startJob } from "@/lib/actions"
import { message } from "@/lib/api"
import { ago, areaName, date, duration } from "@/lib/format"
import type { Job } from "@/lib/types"

type Task = "find_sites" | "pagespeed" | "rescore" | "backfill"

export default function PipelinePage() {
  const { data: meta, error } = useMeta()
  const { data: jobsData } = useJobs()
  const drawer = useJobsDrawer()
  const [refreshOpen, setRefreshOpen] = useState(false)
  const [qCount, setQCount] = useState("10")
  const [qArea, setQArea] = useState("any")
  const jobs = jobsData?.jobs ?? []
  const running = (kind: Job["kind"], match?: (j: Job) => boolean) => jobs.find((j) => j.kind === kind && isActive(j) && (!match || match(j)))

  async function run(url: string, body: unknown) {
    const job = await startJob(url, body)
    if (job) drawer.open(job.id)
  }

  /** A maintenance button: starts the task, or shows the run that is already waiting or going. */
  function taskButton(task: Task, label: string, disabled = false) {
    const job = running(task)
    return job ? (
      <Button variant="outline" onClick={() => drawer.open(job.id)}>
        <JobStatusMark status={job.status} />
        View: {label.toLowerCase()}
      </Button>
    ) : (
      <Button variant="outline" disabled={disabled} onClick={() => void run("/api/jobs/maintenance", { task })}>
        {label}
      </Button>
    )
  }

  const auditJob = running("audit")
  const enrichJob = running("enrich")
  const qualityJob = running("quality")
  const surveyed = meta?.areas.filter((a) => a.places > 0) ?? []
  const totalPlaces = meta?.areas.reduce((n, a) => n + a.places, 0) ?? 0

  return (
    <div className="mx-auto max-w-5xl px-6 pt-4 pb-16">
      <header className="border-b border-rule pb-3">
        <h1 className="text-xl font-semibold">Pipeline</h1>
        <p className="prose-measure text-muted-foreground">Survey an area, audit what was found, then research the leads worth it. Each step feeds the ranked sheet.</p>
      </header>

      {error ? (
        <Alert variant="destructive" className="mt-6">
          <AlertTitle>The pipeline status could not be loaded</AlertTitle>
          <AlertDescription>{message(error)}</AlertDescription>
        </Alert>
      ) : null}

      <Section title="1. Survey an area" aside="From OpenStreetMap, one area at a time" className="mt-6">
        <p className="prose-measure text-muted-foreground">
          Pulls every restaurant mapped inside the area's circle. Surveying an area again refreshes its places and keeps your statuses, notes and research.
        </p>
        {!meta ? (
          <Skeleton className="mt-3 h-64" />
        ) : (
          <table className="mt-3 w-full border-collapse">
            <thead>
              <tr className="text-left">
                {["Area", "Radius", "Places", "Audited", "Surveyed", ""].map((h, i) => (
                  <Lettering as="th" key={i} className="border-b border-rule pr-4 pb-1">
                    {h || <span className="sr-only">Action</span>}
                  </Lettering>
                ))}
              </tr>
            </thead>
            <tbody>
              {meta.areas.map((a) => {
                const job = running("discover", (j) => j.params.area === a.key)
                return (
                  <tr key={a.key} className="border-b border-border">
                    <th scope="row" className="py-1.5 pr-4 text-left font-semibold">
                      {areaName(a.key)}
                    </th>
                    <td className="figure py-1.5 pr-4 text-muted-foreground">{(a.radius_m / 1000).toFixed(1)} km</td>
                    <td className="figure py-1.5 pr-4">{a.places || <span className="text-muted-foreground">Not surveyed</span>}</td>
                    <td className="figure py-1.5 pr-4">{a.places ? (a.audited === a.places ? "All" : `${a.audited} of ${a.places}`) : ""}</td>
                    <td className="py-1.5 pr-4 text-muted-foreground">{a.fetched_at ? date(a.fetched_at) : ""}</td>
                    <td className="py-1.5 text-right">
                      {job ? (
                        <Button variant="outline" size="sm" onClick={() => drawer.open(job.id)}>
                          <JobStatusMark status={job.status} />
                          View
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => void run("/api/jobs/discover", { area: a.key })}>
                          {a.places ? "Survey again" : "Survey"}
                        </Button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="2. Audit websites" aside={meta ? (meta.unaudited ? `${meta.unaudited} places not audited` : totalPlaces ? "Every place has been audited" : undefined) : undefined}>
        <p className="prose-measure text-muted-foreground">
          Checks each listed website: does it load, is it the restaurant's, how good is it. Places with no website take no time. Broken links are re-checked once they are {meta?.limits.url_recheck_days ?? 3} days old.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {auditJob ? (
            <Button variant="outline" onClick={() => drawer.open(auditJob.id)}>
              <JobStatusMark status={auditJob.status} />
              View the running audit
            </Button>
          ) : (
            <>
              <Button onClick={() => void run("/api/jobs/audit", { refresh: false })} disabled={!totalPlaces}>
                Audit new and broken
              </Button>
              <Popover open={refreshOpen} onOpenChange={setRefreshOpen}>
                <PopoverTrigger render={<Button variant="outline" disabled={!totalPlaces} />}>Re-audit everything</PopoverTrigger>
                <PopoverContent align="start" className="w-80 gap-3 p-4">
                  <PopoverHeader>
                    <PopoverTitle>Re-audit all {totalPlaces} places?</PopoverTitle>
                    <PopoverDescription>
                      Every website is fetched and scored again. Google's free PageSpeed service often refuses after a few sites; the audit then carries on with a neutral speed score.
                    </PopoverDescription>
                  </PopoverHeader>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => {
                        setRefreshOpen(false)
                        void run("/api/jobs/audit", { refresh: true })
                      }}
                    >
                      Re-audit everything
                    </Button>
                    <Button variant="ghost" onClick={() => setRefreshOpen(false)}>
                      Not now
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
            </>
          )}
        </div>
        <div className="mt-4 border-t border-border pt-3">
          <Lettering as="h3">Other checks</Lettering>
          <ul className="prose-measure mt-1 text-muted-foreground">
            <li>
              <strong className="font-semibold text-foreground">Find missing websites</strong> guesses domains for places listed without a website and keeps a site only if it shows the restaurant's phone, or its name and area. It audits new places first, and can take a while.
            </li>
            <li>
              <strong className="font-semibold text-foreground">Fill speed scores</strong> asks Google PageSpeed again for sites that have no speed score yet. The free service refuses after a few sites, so run it a little at a time.
            </li>
            <li>
              <strong className="font-semibold text-foreground">Recompute scores</strong> re-reads the stored audits with the current scoring rules. It makes no web requests; run it after the rules change.
            </li>
          </ul>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {taskButton("find_sites", "Find missing websites", !totalPlaces)}
            {taskButton("pagespeed", "Fill speed scores", !totalPlaces)}
            {taskButton("rescore", "Recompute scores", !totalPlaces)}
          </div>
        </div>
      </Section>

      <Section title="3. Find premium restaurants" aside={meta ? `${meta.maps_verified} verified on Google Maps` : undefined}>
        <p className="prose-measure text-muted-foreground">
          Ranks every place by quality from its OpenStreetMap tags, then opens the best ones on Google Maps to read the rating and review count. A restaurant with at least 4.4 stars and 100 reviews becomes Premium on the ranked sheet.
          This reads public Google Maps pages as a logged-out visitor, one place at a time; Google's terms forbid scraping, so keep batches small. A block or captcha is recorded and skipped, never worked around.
          A restaurant Google Maps lists as permanently closed is left out of the ranked sheet. Import saved Maps data picks up pages already read from a lead's own page, so they count here too.
        </p>
        {meta && !meta.scrape.available ? (
          <Alert className="mt-3 border-warn/40 bg-warn-soft text-warn">
            <AlertTitle>Playwright is not installed</AlertTitle>
            <AlertDescription className="text-warn">
              Run <code>pip install playwright</code> and <code>python -m playwright install chromium</code>, then restart this app.
            </AlertDescription>
          </Alert>
        ) : null}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {qualityJob ? (
            <Button variant="outline" onClick={() => drawer.open(qualityJob.id)}>
              <JobStatusMark status={qualityJob.status} />
              View the running check
            </Button>
          ) : (
            <>
              <Select value={qCount} onValueChange={(v) => setQCount(v as string)} items={["5", "10", "25"].map((n) => ({ value: n, label: `${n} places` }))}>
                <SelectTrigger size="sm" aria-label="How many places">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {["5", "10", "25"].map((n) => (
                      <SelectItem key={n} value={n}>
                        {n} places
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              <Select
                value={qArea}
                onValueChange={(v) => setQArea(v as string)}
                items={[{ value: "any", label: "All areas" }, ...surveyed.map((a) => ({ value: a.key, label: areaName(a.key) }))]}
              >
                <SelectTrigger size="sm" aria-label="Area">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="any">All areas</SelectItem>
                    {surveyed.map((a) => (
                      <SelectItem key={a.key} value={a.key}>
                        {areaName(a.key)}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              <Button onClick={() => void run("/api/jobs/quality", { n: Number(qCount), area: qArea === "any" ? null : qArea })} disabled={!totalPlaces || !meta?.scrape.available}>
                Verify best candidates on Maps
              </Button>
            </>
          )}
          {taskButton("backfill", "Import saved Maps data", !totalPlaces)}
        </div>
      </Section>

      <Section title="4. Research a lead" aside="One lead at a time, from its own page">
        <p className="prose-measure text-muted-foreground">
          Research is started from a lead's page with the Get insights button. It runs Claude Code on your subscription inside a workspace that holds only that lead's files, with no access to the rest of this machine.
        </p>
        {meta ? (
          meta.claude?.available ? (
            <p className="mt-2">
              Claude Code {(meta.claude.version ?? "").replace(/\s*\(.*\)$/, "")} found. {enrichJob ? `Researching ${enrichJob.lead?.name ?? "a lead"} now.` : "Nothing is being researched."}
              {enrichJob ? (
                <Button variant="link" size="sm" onClick={() => drawer.open(enrichJob.id)}>
                  View progress
                </Button>
              ) : null}
            </p>
          ) : (
            <Alert className="mt-3 border-warn/40 bg-warn-soft text-warn">
              <AlertTitle>Claude Code was not found</AlertTitle>
              <AlertDescription className="text-warn">Install the Claude Code CLI and sign in, then restart this app. Everything else works without it.</AlertDescription>
            </Alert>
          )
        ) : null}
      </Section>

      <Section title="Recent jobs">
        {jobs.length === 0 ? (
          <p className="text-muted-foreground">Nothing has been run from the app yet.</p>
        ) : (
          <ul>
            {jobs.slice(0, 12).map((j) => (
              <li key={j.id} className="border-b border-border">
                <button type="button" onClick={() => drawer.open(j.id)} className="flex w-full items-center gap-3 py-1.5 text-left hover:bg-muted/60">
                  <JobStatusMark status={j.status} />
                  <span className="min-w-0 flex-1 truncate">{j.title}</span>
                  <span className="figure text-xs text-muted-foreground">{j.started ? duration(j.started, j.ended) : ""}</span>
                  <span className="figure w-24 text-right text-xs text-muted-foreground">{ago(j.created)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}
