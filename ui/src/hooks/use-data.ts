import { useEffect, useRef, useState } from "react"
import useSWR, { mutate } from "swr"

import { fetcher } from "@/lib/api"
import type { Job, JobLine, LeadDetail, LeadList, Meta } from "@/lib/types"

export const keys = {
  meta: "/api/meta",
  leads: "/api/leads?include_excluded=1",
  lead: (key: string) => `/api/leads/${key}`,
  jobs: "/api/jobs",
}

const ACTIVE = new Set(["queued", "running"])
export const isActive = (j: Pick<Job, "status"> | null | undefined) => !!j && ACTIVE.has(j.status)

export function useMeta() {
  return useSWR<Meta>(keys.meta, fetcher, { revalidateOnFocus: false })
}

export function useLeads() {
  return useSWR<LeadList>(keys.leads, fetcher, { keepPreviousData: true })
}

export function useLead(key: string | undefined) {
  return useSWR<LeadDetail>(key ? keys.lead(key) : null, fetcher, { keepPreviousData: false })
}

/** The job list, polled only while something is queued or running. */
export function useJobs() {
  return useSWR<{ jobs: Job[] }>(keys.jobs, fetcher, {
    refreshInterval: (data) => (data?.jobs.some(isActive) ? 2000 : 0),
  })
}

/** Everything that may have changed when a job ends. */
export function refreshAfterJob(job: Job) {
  void mutate(keys.jobs)
  void mutate(keys.leads)
  void mutate(keys.meta)
  if (job.lead) void mutate(keys.lead(job.lead.key))
}

/** One job with its log, read by cursor: each poll asks only for the lines after the last one seen. */
export function useJobLog(id: string | null | undefined) {
  const [state, setState] = useState<{ id: string; job: Job; lines: JobLine[] } | null>(null)
  const cursor = useRef(0)

  useEffect(() => {
    if (!id) return
    let stopped = false
    let timer: ReturnType<typeof setTimeout>
    cursor.current = 0

    async function tick() {
      try {
        const res = await fetcher<{ job: Job; lines: JobLine[]; next: number }>(`/api/jobs/${id}?after=${cursor.current}`)
        if (stopped) return
        const first = cursor.current === 0
        cursor.current = res.next
        setState((prev) => ({
          id: id!,
          job: res.job,
          lines: !first && prev && prev.id === id ? [...prev.lines, ...res.lines] : res.lines,
        }))
        if (isActive(res.job)) timer = setTimeout(tick, 1000)
        else refreshAfterJob(res.job)
      } catch {
        if (!stopped) timer = setTimeout(tick, 3000)
      }
    }
    void tick()
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [id])

  return state?.id === id ? state : null
}
