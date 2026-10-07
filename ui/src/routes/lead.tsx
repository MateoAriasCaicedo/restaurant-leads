import { ArrowLeftIcon } from "lucide-react"
import { useState, type ReactNode } from "react"
import { Link, useParams, useSearchParams } from "react-router"

import { DesignSystemTab } from "@/components/lead/design"
import { EnrichButton, EnrichProgress } from "@/components/lead/enrich"
import { MaterialsTab } from "@/components/lead/materials"
import { ContactCard, ContactLog, PrivateNote } from "@/components/lead/outreach"
import { AuditSection, BlockPlot, MapFacts, ScoreSection } from "@/components/lead/overview"
import { AnalysisTab, BuildPlanTab, MenuTab, PitchSection, PresenceTab } from "@/components/lead/research"
import { Lettering, STATUS_HELP, TierZone, VerdictMark, WebState } from "@/components/plan"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button, buttonVariants } from "@/components/ui/button"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useLead, useMeta } from "@/hooks/use-data"
import { setStatus } from "@/lib/actions"
import { ApiError, message } from "@/lib/api"
import { areaName, date, label, plotNo, webState } from "@/lib/format"
import type { LeadDetail, Meta, Status } from "@/lib/types"

export default function LeadPage() {
  const { key } = useParams()
  const { data: lead, error, isLoading } = useLead(key)
  const { data: meta } = useMeta()

  if (error) {
    const missing = error instanceof ApiError && error.status === 404
    return (
      <Empty className="h-full">
        <EmptyHeader>
          <EmptyTitle>{missing ? "No plot with this number" : "This lead could not be loaded"}</EmptyTitle>
          <EmptyDescription>{missing ? "It may have been removed from the map since the last survey." : message(error)}</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Link to="/" className={buttonVariants({ variant: "outline" })}>
            Back to the sheet
          </Link>
        </EmptyContent>
      </Empty>
    )
  }
  if (isLoading || !lead) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-80" />
        <Skeleton className="h-6 w-96" />
        <Skeleton className="h-72 w-full max-w-4xl" />
      </div>
    )
  }
  return <Lead key={lead.key} lead={lead} meta={meta} />
}

function Lead({ lead, meta }: { lead: LeadDetail; meta?: Meta }) {
  const [params, setParams] = useSearchParams()
  const [watch, setWatch] = useState<string | null>(null)
  const p = lead.place
  const profile = lead.profile
  const enrichJob = lead.active_job?.kind === "enrich" ? lead.active_job.id : null
  if (enrichJob && enrichJob !== watch) setWatch(enrichJob)
  const busy = !!enrichJob || lead.active_job?.kind === "scrape"

  const tabs = [
    { id: "overview", label: "Overview" },
    ...(profile
      ? [
          { id: "analysis", label: "Analysis" },
          { id: "menu", label: "Menu" },
          { id: "presence", label: "Presence" },
          { id: "build", label: "Build plan" },
          { id: "design", label: "Design system" },
        ]
      : [{ id: "research", label: "Research" }]),
    { id: "materials", label: "Materials" },
  ]
  const tab = tabs.some((t) => t.id === params.get("tab")) ? params.get("tab")! : "overview"
  const setTab = (id: string) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev)
      if (id === "overview") next.delete("tab")
      else next.set("tab", id)
      return next
    }, { replace: true })

  const statusItems = [{ value: "none", label: "No status" }, ...(meta?.statuses ?? []).map((s) => ({ value: s as string, label: label(s) }))]
  const struck = lead.status === "rejected" || !!lead.excluded_reason

  return (
    <div className="mx-auto max-w-[88rem] px-6 pt-4 pb-16">
      <Link to="/" className="inline-flex items-center gap-1 text-[0.8125rem] text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-3.5" aria-hidden="true" />
        Leads
      </Link>

      <header className="mt-2 flex flex-wrap items-end justify-between gap-x-6 gap-y-4 border-b border-rule pb-4">
        <div className="min-w-0">
          <h1 className={`text-2xl leading-8 font-semibold ${struck ? "line-through decoration-1" : ""}`}>{p.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
            <WebState state={webState(lead)} />
            {profile ? <VerdictMark verdict={profile.operating_status?.verdict ?? "unknown"} /> : <span className="text-muted-foreground">Not researched yet</span>}
            {lead.excluded_reason ? <span className="text-bad">Excluded from the ranking: {lead.excluded_reason}</span> : null}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Select
              value={lead.status ?? "none"}
              onValueChange={(v) => void setStatus(lead.key, v === "none" ? null : (v as Status), { from: lead.status, name: p.name })}
              items={statusItems}
            >
            <SelectTrigger aria-label="Status" className="min-w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {statusItems.map((s) => (
                  <SelectItem key={s.value} value={s.value} title={STATUS_HELP[s.value as Status]}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectGroup>
              </SelectContent>
            </Select>
            <EnrichButton lead={lead} meta={meta} onStarted={(job) => setWatch(job.id)} />
          </div>
        </div>
        {/* the plan's title block: the plot's reference facts, ruled */}
        <dl className="grid grid-cols-2 border border-rule text-[0.8125rem] sm:grid-cols-4">
          {(
            [
              ["Plot", <span className="plot-no">{plotNo(p.place_id)}</span>],
              ["Area", areaName(p.area)],
              [
                "Sell score",
                <span className="inline-flex items-center gap-1.5">
                  <TierZone tier={lead.score.tier} className="size-4" />
                  <span className="figure font-semibold">{lead.score.total}</span>
                </span>,
              ],
              ["Surveyed", p.fetched_at ? date(p.fetched_at) : ""],
            ] as [string, ReactNode][]
          ).map(([k, v], i) => (
            <div key={k} className={`min-w-28 px-3 py-1.5 ${i < 3 ? "sm:border-r" : ""} ${i % 2 === 0 ? "border-r sm:border-r" : ""} ${i < 2 ? "border-b sm:border-b-0" : ""} border-rule`}>
              <Lettering as="dt">{k}</Lettering>
              <dd className="leading-5">{v}</dd>
            </div>
          ))}
        </dl>
      </header>

      <div className="mt-6 grid gap-x-10 gap-y-8 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="min-w-0">
          {watch ? <EnrichProgress jobId={watch} onDismiss={() => setWatch(null)} /> : null}
          {lead.profile_problems && Object.values(lead.profile_problems).some((x) => x.length) ? (
            <Alert variant="destructive" className="mb-6">
              <AlertTitle>The saved analysis files have problems</AlertTitle>
              <AlertDescription>
                {Object.values(lead.profile_problems).flat().slice(0, 5).join("; ")}. Research the lead again, or fix the files in leads/{lead.slug}/profile.
              </AlertDescription>
            </Alert>
          ) : null}

          <Tabs value={tab} onValueChange={(v) => setTab(v as string)}>
            <TabsList
              variant="line"
              className="mb-5 w-full justify-start overflow-x-auto border-b border-border [mask-image:linear-gradient(to_right,black_82%,transparent)] [scrollbar-width:none] sm:[mask-image:none]"
            >
              {tabs.map((t) => (
                <TabsTrigger key={t.id} value={t.id} className="flex-none">
                  {t.label}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value="overview">
              <ScoreSection lead={lead} />
              {profile ? <PitchSection profile={profile} /> : null}
              <AuditSection lead={lead} />
              <BlockPlot lead={lead} />
              <MapFacts lead={lead} />
            </TabsContent>

            {profile ? (
              <>
                <TabsContent value="analysis">
                  {lead.profile_meta ? (
                    <p className="mb-5 text-[0.8125rem] text-muted-foreground">
                      Researched {date(lead.profile_meta.created_at)}. Written by a model from public sources: treat numbers and dates as leads to verify, not facts.
                    </p>
                  ) : null}
                  <AnalysisTab profile={profile} />
                </TabsContent>
                <TabsContent value="menu">
                  <MenuTab lead={lead} menu={lead.menu} />
                </TabsContent>
                <TabsContent value="presence">
                  <PresenceTab presence={lead.presence} />
                </TabsContent>
                <TabsContent value="build">
                  <BuildPlanTab lead={lead} profile={profile} />
                </TabsContent>
                <TabsContent value="design">
                  <DesignSystemTab lead={lead} meta={meta} onStarted={(job) => setWatch(job.id)} />
                </TabsContent>
              </>
            ) : (
              <TabsContent value="research">
                <Empty className="border border-dashed border-input py-12">
                  <EmptyHeader>
                    <EmptyTitle>This lead has not been researched</EmptyTitle>
                    <EmptyDescription>
                      Research reads their site, the photos and menu you add, and the public web. It tells you whether they are open, what customers say, what their menu is, how a site for them should look, and three ways to open the conversation.
                    </EmptyDescription>
                  </EmptyHeader>
                  <EmptyContent className="flex-row justify-center">
                    <Button variant="outline" onClick={() => setTab("materials")}>
                      Add photos first
                    </Button>
                    <EnrichButton lead={lead} meta={meta} onStarted={(job) => setWatch(job.id)} />
                  </EmptyContent>
                </Empty>
              </TabsContent>
            )}

            <TabsContent value="materials">
              <MaterialsTab lead={lead} meta={meta} busy={busy} />
            </TabsContent>

          </Tabs>
        </div>

        <aside className="flex flex-col gap-8">
          <ContactCard lead={lead} />
          <PrivateNote key={lead.private_note.updated_at ?? 0} lead={lead} />
          <ContactLog lead={lead} meta={meta} />
        </aside>
      </div>
    </div>
  )
}

