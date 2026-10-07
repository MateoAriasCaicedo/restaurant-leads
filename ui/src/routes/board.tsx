import { useState, type DragEvent } from "react"
import { Link } from "react-router"

import { Lettering, STATUS_HELP, TierZone, VerdictMark } from "@/components/plan"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { buttonVariants } from "@/components/ui/button"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { useLeads, useMeta } from "@/hooks/use-data"
import { setStatus } from "@/lib/actions"
import { message } from "@/lib/api"
import { ago, label } from "@/lib/format"
import type { LeadRow, Status } from "@/lib/types"
import { cn } from "@/lib/utils"

const ORDER: Status[] = ["approved", "enriched", "ready", "contacted", "rejected"]

export default function BoardPage() {
  const { data, error, isLoading } = useLeads()
  const { data: meta } = useMeta()
  const [over, setOver] = useState<Status | null>(null)
  const statuses = ORDER.filter((s) => !meta || meta.statuses.includes(s))
  const withStatus = data?.rows.filter((r) => r.status) ?? []
  const items = statuses.map((s) => ({ value: s as string, label: label(s) }))

  function onDrop(e: DragEvent, status: Status) {
    e.preventDefault()
    setOver(null)
    const key = e.dataTransfer.getData("text/plain")
    const row = withStatus.find((r) => r.key === key)
    if (row && row.status !== status) void setStatus(key, status)
  }

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-rule px-6 py-3">
        <h1 className="text-xl font-semibold">Board</h1>
        <p className="text-muted-foreground">
          Every lead you have acted on, by where it stands.
          {data ? ` ${data.rows.length - withStatus.length} ranked leads have no status yet and stay on the sheet.` : ""}
        </p>
      </header>

      {error ? (
        <Alert variant="destructive" className="m-6 w-auto">
          <AlertTitle>The board could not be loaded</AlertTitle>
          <AlertDescription>{message(error)}</AlertDescription>
        </Alert>
      ) : isLoading ? (
        <div className="grid grid-cols-5 gap-4 p-6">
          {statuses.map((s) => (
            <Skeleton key={s} className="h-64" />
          ))}
        </div>
      ) : withStatus.length === 0 ? (
        <Empty className="flex-1">
          <EmptyHeader>
            <EmptyTitle>Nothing on the board yet</EmptyTitle>
            <EmptyDescription>Approve a lead on the sheet and it appears here. From then on the board follows it through research, contact and the answer.</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Link to="/" className={buttonVariants()}>
              Go to the sheet
            </Link>
          </EmptyContent>
        </Empty>
      ) : (
        <div className="grid min-h-0 flex-1 auto-cols-[minmax(15rem,1fr)] grid-flow-col overflow-x-auto">
          {statuses.map((s) => {
            const rows = withStatus.filter((r) => r.status === s)
            return (
              <section
                key={s}
                aria-labelledby={`col-${s}`}
                onDragOver={(e) => {
                  e.preventDefault()
                  setOver(s)
                }}
                onDragLeave={() => setOver((o) => (o === s ? null : o))}
                onDrop={(e) => onDrop(e, s)}
                className={cn("flex min-h-0 flex-col border-r border-border last:border-r-0", over === s && "bg-live-soft")}
              >
                <div className="border-b border-rule px-4 py-2">
                  <div className="flex items-baseline justify-between">
                    <h2 id={`col-${s}`} className="font-semibold">
                      {label(s)}
                    </h2>
                    <span className="figure text-muted-foreground">{rows.length}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{STATUS_HELP[s]}</p>
                </div>
                <ul className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-3">
                  {rows.length === 0 ? <li className="px-1 text-[0.8125rem] text-muted-foreground">None. Drag a lead here, or use its menu.</li> : null}
                  {rows.map((r) => (
                    <Card key={r.key} r={r} items={items} />
                  ))}
                </ul>
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}

function Card({ r, items }: { r: LeadRow; items: { value: string; label: string }[] }) {
  return (
    <li
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", r.key)
        e.dataTransfer.effectAllowed = "move"
      }}
      className="cursor-grab border border-border bg-card p-2.5 active:cursor-grabbing"
    >
      <div className="flex items-start gap-2">
        <TierZone tier={r.tier} className="mt-0.5" />
        <div className="min-w-0 flex-1">
          <Link to={`/leads/${r.key}`} className={cn("block truncate font-semibold hover:underline", r.status === "rejected" && "text-muted-foreground line-through decoration-1")}>
            {r.name}
          </Link>
          <div className="truncate text-xs text-muted-foreground">
            <span className="figure">{r.sell_score}</span> · {r.reasons.slice(0, 2).join(" · ") || "no signals"}
          </div>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="min-w-0 truncate text-xs text-muted-foreground">
          {r.last_contact ? `${label(r.last_contact.outcome)} · ${ago(r.last_contact.at)}` : r.has_profile ? <VerdictMark verdict={r.operating_status || "unknown"} /> : "Not researched"}
        </div>
        <Select value={r.status} onValueChange={(v) => void setStatus(r.key, v as Status)} items={items}>
          <SelectTrigger size="sm" aria-label={`Move ${r.name}`} className="h-6 gap-1 border-0 px-1 text-xs">
            <Lettering>Move</Lettering>
            <SelectValue className="sr-only" />
          </SelectTrigger>
          <SelectContent align="end">
            <SelectGroup>
              {items.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>
    </li>
  )
}
