import { ActivityIcon, Columns3Icon, TablePropertiesIcon, WorkflowIcon } from "lucide-react"
import { lazy, Suspense, useEffect } from "react"
import { BrowserRouter, NavLink, Route, Routes } from "react-router"
import { SWRConfig } from "swr"

import { JobsProvider, useJobsDrawer } from "@/components/jobs"
import { Skeleton } from "@/components/ui/skeleton"
import { Toaster } from "@/components/ui/sonner"
import { Spinner } from "@/components/ui/spinner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { isActive, useJobs, useMeta } from "@/hooks/use-data"
import { cn } from "@/lib/utils"
import LeadsPage from "@/routes/leads"

const LeadPage = lazy(() => import("@/routes/lead"))
const BoardPage = lazy(() => import("@/routes/board"))
const PipelinePage = lazy(() => import("@/routes/pipeline"))

const NAV = [
  { to: "/", label: "Leads", icon: TablePropertiesIcon, end: true },
  { to: "/board", label: "Board", icon: Columns3Icon, end: false },
  { to: "/pipeline", label: "Pipeline", icon: WorkflowIcon, end: false },
]

function Rail() {
  const { data: meta } = useMeta()
  const { data: jobs } = useJobs()
  const drawer = useJobsDrawer()
  const active = jobs?.jobs.filter(isActive) ?? []
  const name = meta?.app_name ?? ""

  useEffect(() => {
    document.title = name ? `Leads · ${name}` : "Leads"
  }, [name])

  return (
    <aside className="flex shrink-0 flex-col bg-rail text-rail-foreground md:w-52">
      <div className="border-b border-rail-line px-4 py-3 text-base font-semibold md:py-4">{name || " "}</div>
      <nav aria-label="Main" className="flex gap-1 px-2 py-2 md:flex-col md:py-3">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive: on }) =>
              cn(
                "flex items-center gap-2.5 px-2.5 py-1.5 font-medium outline-offset-0",
                on ? "bg-live text-white" : "text-rail-foreground hover:bg-rail-line",
              )
            }
          >
            <n.icon className="size-4" aria-hidden="true" />
            {n.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto hidden border-t border-rail-line p-2 md:block">
        <button
          type="button"
          onClick={() => drawer.open(active[0]?.id)}
          className="flex w-full items-center gap-2.5 px-2.5 py-1.5 text-left font-medium hover:bg-rail-line"
        >
          {active.length ? <Spinner className="size-4 text-white" /> : <ActivityIcon className="size-4" aria-hidden="true" />}
          <span className="min-w-0 flex-1 truncate">{active.length ? active[0].title : "Jobs"}</span>
          {active.length > 1 ? <span className="figure text-xs text-rail-muted">+{active.length - 1}</span> : null}
        </button>
      </div>
    </aside>
  )
}

function PageFallback() {
  return (
    <div className="flex flex-col gap-3 p-6">
      <Skeleton className="h-7 w-64" />
      <Skeleton className="h-4 w-96" />
      <Skeleton className="h-64 w-full" />
    </div>
  )
}

export default function App() {
  return (
    <SWRConfig value={{ revalidateOnFocus: true, dedupingInterval: 1500, shouldRetryOnError: false }}>
      <TooltipProvider delay={250}>
        <BrowserRouter>
          <JobsProvider>
            <div className="flex h-dvh flex-col md:flex-row">
              <Rail />
              <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">
                <Suspense fallback={<PageFallback />}>
                  <Routes>
                    <Route path="/" element={<LeadsPage />} />
                    <Route path="/leads/:key" element={<LeadPage />} />
                    <Route path="/board" element={<BoardPage />} />
                    <Route path="/pipeline" element={<PipelinePage />} />
                    <Route path="*" element={<LeadsPage />} />
                  </Routes>
                </Suspense>
              </main>
            </div>
            <Toaster position="bottom-right" />
          </JobsProvider>
        </BrowserRouter>
      </TooltipProvider>
    </SWRConfig>
  )
}
