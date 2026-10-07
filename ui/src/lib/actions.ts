import { toast } from "sonner"
import { mutate } from "swr"

import { keys } from "@/hooks/use-data"
import { message, send } from "@/lib/api"
import type { Job, LeadDetail, LeadList, Status } from "@/lib/types"

// The status each lead had before its last change in this session, so a rejection can be undone back to
// "enriched" or "contacted" rather than to nothing.
const previous = new Map<string, Status | null>()

/** Set or clear a lead's status. The list and the lead page update at once and roll back if the server
 *  refuses. Rejecting shows an undo that restores whatever the status was before. */
export async function setStatus(key: string, status: Status | null, opts: { from?: Status | null; name?: string } = {}) {
  const patchList = (data?: LeadList): LeadList | undefined =>
    data && { ...data, rows: data.rows.map((r) => (r.key === key ? { ...r, status: status ?? "" } : r)) }
  const patchLead = (data?: LeadDetail): LeadDetail | undefined => data && { ...data, status }
  if (opts.from !== undefined && opts.from !== status) previous.set(key, opts.from)
  try {
    await Promise.all([
      mutate(
        keys.leads,
        async (current?: LeadList) => {
          await send("PUT", `/api/leads/${key}/status`, { status })
          return patchList(current)
        },
        { optimisticData: (current?: LeadList) => patchList(current) as LeadList, rollbackOnError: true, revalidate: false },
      ),
      mutate(keys.lead(key), (current?: LeadDetail) => patchLead(current), { revalidate: false }),
    ])
  } catch (err) {
    void mutate(keys.lead(key))
    toast.error(message(err))
    return
  }
  if (status === "rejected") {
    const back = opts.from ?? null
    toast(`${opts.name ?? "Lead"} rejected`, {
      description: back ? `It was ${back}.` : undefined,
      action: { label: "Undo", onClick: () => void setStatus(key, back, { from: "rejected", name: opts.name }) },
    })
  }
}

/** Undo a rejection: back to the status before it if this session saw it, otherwise no status. */
export function unreject(key: string, name?: string) {
  const back = previous.get(key) ?? null
  return setStatus(key, back === "rejected" ? null : back, { from: "rejected", name })
}

/** Start a pipeline job and hand back the job, or null (with a toast) if the server refused. */
export async function startJob(url: string, body?: unknown): Promise<Job | null> {
  try {
    const res = await send<{ job: Job }>("POST", url, body ?? {})
    void mutate(keys.jobs)
    return res.job
  } catch (err) {
    toast.error(message(err))
    return null
  }
}
