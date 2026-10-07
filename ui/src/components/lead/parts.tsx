// Small layout pieces shared by the lead page's sections.
import { DownloadIcon } from "lucide-react"
import type { ReactNode } from "react"

import { Lettering } from "@/components/plan"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function Section({ title, aside, children, className }: { title: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("mt-8 first:mt-0", className)}>
      <div className="mb-2 flex items-baseline justify-between gap-3 border-b border-rule pb-1">
        <h2 className="text-base font-semibold">{title}</h2>
        {aside ? <div className="text-xs text-muted-foreground">{aside}</div> : null}
      </div>
      {children}
    </section>
  )
}

export function Sub({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("mt-4 first:mt-0", className)}>
      <Lettering as="h3" className="mb-1">
        {title}
      </Lettering>
      {children}
    </div>
  )
}

/** A download served by the local API (a Markdown brief for the agent that builds the site). */
export function DownloadLink({ href, title, children }: { href: string; title: string; children: ReactNode }) {
  return (
    <a href={href} download title={title} className={cn(buttonVariants({ variant: "outline", size: "sm" }), "text-foreground")}>
      <DownloadIcon data-icon="inline-start" />
      {children}
    </a>
  )
}

/** Text written by the analysis. Rendered as plain text, never as markup. */
export function Prose({ children, className }: { children: string | null | undefined; className?: string }) {
  if (!children || !String(children).trim()) return <p className="text-muted-foreground">Nothing recorded.</p>
  return <p className={cn("prose-measure whitespace-pre-line", className)}>{String(children)}</p>
}

export function Bullets({ items, empty = "Nothing recorded.", ordered, className }: { items: (string | undefined | null)[] | undefined | null; empty?: string; ordered?: boolean; className?: string }) {
  const list = (Array.isArray(items) ? items : []).filter((x): x is string => typeof x === "string" && x.trim() !== "")
  if (!list.length) return <p className="text-muted-foreground">{empty}</p>
  const Tag = ordered ? "ol" : "ul"
  return (
    <Tag className={cn("prose-measure flex flex-col gap-1 pl-5 marker:text-faint", ordered ? "list-decimal marker:text-muted-foreground" : "list-disc", className)}>
      {list.map((x, i) => (
        <li key={i}>{x}</li>
      ))}
    </Tag>
  )
}

export function Chips({ items }: { items: (string | undefined | null)[] | undefined | null }) {
  const list = (Array.isArray(items) ? items : []).filter((x): x is string => typeof x === "string" && x.trim() !== "")
  if (!list.length) return <span className="text-muted-foreground">Nothing recorded.</span>
  return (
    <ul className="flex flex-wrap gap-1.5">
      {list.map((x, i) => (
        <li key={i} className="border border-border bg-card px-1.5 py-0.5 text-[0.8125rem]">
          {x}
        </li>
      ))}
    </ul>
  )
}

export function Facts({ rows, className }: { rows: [string, ReactNode][]; className?: string }) {
  const shown = rows.filter(([, v]) => v !== null && v !== undefined && v !== "" && v !== false)
  if (!shown.length) return <p className="text-muted-foreground">Nothing recorded.</p>
  return (
    <dl className={cn("grid grid-cols-[minmax(7rem,auto)_1fr] gap-x-4 gap-y-1.5", className)}>
      {shown.map(([k, v]) => (
        <div key={k} className="contents">
          <Lettering as="dt" className="pt-0.5">
            {k}
          </Lettering>
          <dd className="min-w-0 break-words">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

export function Muted({ children }: { children: ReactNode }) {
  return <span className="text-muted-foreground">{children}</span>
}
