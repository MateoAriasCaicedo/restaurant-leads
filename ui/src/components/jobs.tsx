import { CheckIcon, SquareIcon, XIcon } from "lucide-react"
import { createContext, use, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { toast } from "sonner"

import { Lettering, Mark } from "@/components/plan"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Spinner } from "@/components/ui/spinner"
import { isActive, useJobLog, useJobs } from "@/hooks/use-data"
import { message, send } from "@/lib/api"
import { ago, duration } from "@/lib/format"
import type { Job, JobStatus, JobStep } from "@/lib/types"
import { cn } from "@/lib/utils"

const TONE: Record<JobStatus, "muted" | "live" | "good" | "bad" | "warn"> = {
  queued: "muted",
  running: "live",
  succeeded: "good",
  failed: "bad",
  cancelled: "muted",
  interrupted: "warn",
}
const STATUS_TEXT: Record<JobStatus, string> = {
  queued: "Waiting",
  running: "Running",
  succeeded: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
  interrupted: "Interrupted",
}

export function JobStatusMark({ status }: { status: JobStatus }) {
  return <Mark tone={TONE[status]}>{STATUS_TEXT[status]}</Mark>
}

const JobsContext = createContext<{ open: (id?: string) => void }>({ open: () => {} })
export const useJobsDrawer = () => use(JobsContext)

export function JobsProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ open: boolean; id?: string }>({ open: false })
  const value = useMemo(() => ({ open: (id?: string) => setState({ open: true, id }) }), [])
  return (
    <JobsContext value={value}>
      {children}
      <Sheet open={state.open} onOpenChange={(open) => setState((s) => ({ ...s, open }))}>
        <SheetContent className="w-full gap-0 data-[side=right]:sm:max-w-xl">
          <SheetHeader className="border-b border-rule">
            <SheetTitle>Jobs</SheetTitle>
            <SheetDescription>Pipeline runs and analyses, newest first. Discover and audit queue up; analyses run one at a time.</SheetDescription>
          </SheetHeader>
          {state.open ? <JobList selected={state.id} onSelect={(id) => setState({ open: true, id })} /> : null}
        </SheetContent>
      </Sheet>
    </JobsContext>
  )
}

function JobList({ selected, onSelect }: { selected?: string; onSelect: (id?: string) => void }) {
  const { data } = useJobs()
  const jobs = data?.jobs ?? []
  const current = selected ?? jobs[0]?.id
  if (data && jobs.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>No jobs yet</EmptyTitle>
          <EmptyDescription>Discovering an area, auditing websites and researching a lead all show up here with their log.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }
  return (
    <ul className="min-h-0 flex-1 overflow-y-auto">
      {jobs.map((j) => (
        <li key={j.id} className="border-b border-border">
          <button
            type="button"
            onClick={() => onSelect(j.id === current ? undefined : j.id)}
            aria-expanded={j.id === current}
            className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-muted/60"
          >
            <JobStatusMark status={j.status} />
            <span className="min-w-0 flex-1 truncate font-medium">{j.title}</span>
            <span className="figure shrink-0 text-xs text-muted-foreground">{ago(j.created)}</span>
          </button>
          {j.id === current ? (
            <div className="px-4 pb-4">
              <JobLog id={j.id} />
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  )
}

function StepDot({ step }: { step: JobStep }) {
  if (step.status === "running") return <Spinner className="size-3.5 text-live" />
  if (step.status === "done") return <CheckIcon className="size-3.5 text-good" aria-hidden="true" />
  if (step.status === "failed") return <XIcon className="size-3.5 text-bad" aria-hidden="true" />
  return <span className="mx-[3px] block size-2 border border-faint" aria-hidden="true" />
}

export function JobSteps({ job }: { job: Job }) {
  if (job.steps.length < 2) return null
  return (
    <ol className="flex flex-col gap-1.5">
      {job.steps.map((s) => (
        <li key={s.name} className={cn("flex items-center gap-2", s.status === "pending" && "text-muted-foreground")}>
          <StepDot step={s} />
          <span className={cn(s.status === "running" && "font-medium")}>{s.label}</span>
          {s.started ? <span className="figure text-xs text-muted-foreground">{duration(s.started, s.ended ?? null)}</span> : null}
          <span className="sr-only">{s.status}</span>
        </li>
      ))}
    </ol>
  )
}

/** A job's steps and live log. Follows new lines unless the reader has scrolled up. */
export function JobLog({ id, hideSteps }: { id: string; hideSteps?: boolean }) {
  const state = useJobLog(id)
  const box = useRef<HTMLOListElement>(null)
  const follow = useRef(true)
  const [cancelling, setCancelling] = useState(false)
  const count = state?.lines.length ?? 0

  useEffect(() => {
    const el = box.current
    if (el && follow.current) el.scrollTop = el.scrollHeight
  }, [count])

  if (!state) {
    return (
      <div className="flex items-center gap-2 py-2 text-muted-foreground">
        <Spinner /> Loading the log
      </div>
    )
  }
  const { job, lines } = state

  async function cancel() {
    setCancelling(true)
    try {
      await send("POST", `/api/jobs/${job.id}/cancel`)
    } catch (err) {
      toast.error(message(err))
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <JobStatusMark status={job.status} />
        {job.started ? <span className="figure text-xs text-muted-foreground">{duration(job.started, job.ended)}</span> : null}
        {isActive(job) ? (
          <Button variant="outline" size="xs" onClick={cancel} disabled={cancelling} className="ml-auto">
            <SquareIcon data-icon="inline-start" />
            Cancel
          </Button>
        ) : null}
      </div>
      {hideSteps ? null : <JobSteps job={job} />}
      {job.error ? (
        <Alert variant="destructive">
          <AlertTitle>{job.status === "interrupted" ? "Interrupted" : "This job failed"}</AlertTitle>
          <AlertDescription>{job.error}</AlertDescription>
        </Alert>
      ) : null}
      <div>
        <Lettering as="div" className="mb-1">
          Log
        </Lettering>
        <ol
          ref={box}
          tabIndex={0}
          aria-label="Job log"
          onScroll={(e) => {
            const el = e.currentTarget
            follow.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24
          }}
          className="max-h-72 overflow-y-auto border border-border bg-card px-3 py-2 text-xs leading-5"
        >
          {lines.length === 0 ? <li className="text-muted-foreground">{isActive(job) ? "Waiting for output" : "No output."}</li> : null}
          {lines.map((l) => (
            <li
              key={l.seq}
              className={cn(
                "break-words whitespace-pre-wrap",
                l.level === "warn" && "text-warn",
                l.level === "error" && "font-medium text-bad",
                l.level === "note" && "text-muted-foreground",
              )}
            >
              {l.text}
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
