// The researched profile. Every string here was written by a model reading public web content: it is
// rendered as plain text, and URLs become links only through <Ext>, which allows http(s) and nothing else.
import type { ReactNode } from "react"

import { Bullets, Chips, DownloadLink, Facts, Muted, Prose, Section, Sub } from "@/components/lead/parts"
import { Ext, Lettering, Mark, VerdictMark } from "@/components/plan"
import { cop, label } from "@/lib/format"
import type { LeadDetail, Level, Menu, Presence, Profile } from "@/lib/types"

const LEVEL_TONE: Record<Level, "good" | "warn" | "bad"> = { high: "good", medium: "warn", low: "bad" }
const arr = <T,>(v: T[] | undefined | null): T[] => (Array.isArray(v) ? v : [])

function LevelMark({ level, suffix = "" }: { level?: Level; suffix?: string }) {
  return level && LEVEL_TONE[level] ? <Mark tone={LEVEL_TONE[level]}>{level + suffix}</Mark> : null
}

const HEX = /^\s*(#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?)\b[\s:,-]*(.*)$/

export function Palette({ items }: { items: string[] | undefined }) {
  const list = arr(items).filter((x) => typeof x === "string")
  if (!list.length) return <Muted>Nothing recorded.</Muted>
  return (
    <ul className="flex flex-col gap-1">
      {list.map((s, i) => {
        const m = HEX.exec(s)
        return (
          <li key={i} className="flex items-center gap-2">
            <span className="size-4 shrink-0 border border-rule" style={m ? { background: m[1] } : undefined} aria-hidden="true" />
            {m ? (
              <>
                <span className="plot-no text-xs uppercase">{m[1]}</span>
                <span>{m[2]}</span>
              </>
            ) : (
              <span>{s}</span>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export function OperatingStatus({ profile }: { profile: Profile }) {
  const op = profile.operating_status ?? {}
  const closed = op.verdict === "closed" || op.verdict === "likely_closed"
  return (
    <Section title="Is it operating?">
      <div className="flex flex-wrap items-center gap-2">
        <VerdictMark verdict={op.verdict ?? "unknown"} />
        <LevelMark level={op.confidence} suffix=" confidence" />
      </div>
      <Prose className="mt-2">{op.reasoning}</Prose>
      {closed ? <p className="mt-2 font-medium text-bad">Check that it is open before pitching.</p> : null}
    </Section>
  )
}

export function PitchSection({ profile }: { profile: Profile }) {
  return (
    <Section title="Pitch hooks">
      <Bullets items={profile.pitch_hooks} ordered empty="The analysis produced no hooks." />
      <Sub title="Gaps in their web presence">
        <Bullets items={profile.web_gaps} />
      </Sub>
    </Section>
  )
}

export function AnalysisTab({ profile }: { profile: Profile }) {
  const id = profile.identity ?? {}
  const vis = profile.visual_identity ?? {}
  const rep = profile.reputation ?? {}
  const dd = profile.design_direction ?? {}
  const conf = arr(profile.confidence)
  return (
    <>
      <OperatingStatus profile={profile} />
      <PitchSection profile={profile} />
      <Section title="Who they are">
        <Facts
          rows={[
            ["Cuisine", <Chips items={id.cuisine} />],
            ["Specialties", arr(id.specialties).length ? <Chips items={id.specialties} /> : null],
            ["Price tier", id.price_tier ? label(id.price_tier) : null],
            ["Audience", id.audience],
            ["Positioning", id.positioning],
            ["Tone of voice", profile.tone_of_voice],
          ]}
        />
      </Section>
      <Section title="Reputation">
        <Prose>{rep.summary}</Prose>
        {rep.ratings_overview ? <p className="prose-measure mt-2 text-muted-foreground">{rep.ratings_overview}</p> : null}
        <div className="mt-4 grid gap-6 sm:grid-cols-2">
          <Sub title="Praise" className="mt-0">
            <Bullets items={rep.praise} />
          </Sub>
          <Sub title="Complaints" className="mt-0">
            <Bullets items={rep.complaints} empty="None found." />
          </Sub>
        </div>
        <Sub title="Online activity">
          <Prose>{profile.online_activity}</Prose>
        </Sub>
        <Sub title="Against the neighbours">
          <Prose>{profile.competitive_landscape}</Prose>
        </Sub>
      </Section>
      <Section title="How they look today">
        <Facts
          rows={[
            ["Vibe", vis.vibe],
            ["Palette", <Palette items={vis.palette} />],
            ["Typography", vis.typography],
            ["Photo style", vis.photo_style],
          ]}
        />
      </Section>
      <Section title="Design direction for their site">
        <Sub title="Site structure">
          <Bullets items={dd.site_structure} ordered />
        </Sub>
        <Facts
          className="mt-4"
          rows={[
            ["Menu experience", dd.menu_experience],
            ["Palette", dd.palette_suggestion],
            ["Typography", dd.typography_suggestion],
          ]}
        />
      </Section>
      <Section title="How sure the analysis is" aside="Low means a guess, or too little material">
        {conf.length ? (
          <table className="w-full border-collapse text-[0.8125rem]">
            <thead>
              <tr className="text-left">
                {["Field", "Confidence", "Source", "Note"].map((h) => (
                  <Lettering as="th" key={h} className="pr-3 pb-1">
                    {h}
                  </Lettering>
                ))}
              </tr>
            </thead>
            <tbody>
              {conf.map((c, i) => (
                <tr key={i} className="border-t border-border align-top">
                  <td className="py-1.5 pr-3 font-medium">{label(String(c.field ?? ""))}</td>
                  <td className="py-1.5 pr-3">
                    <LevelMark level={c.level} />
                  </td>
                  <td className="py-1.5 pr-3 whitespace-nowrap text-muted-foreground">{c.source}</td>
                  <td className="py-1.5 text-muted-foreground">{c.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <Muted>The analysis did not rate its own confidence.</Muted>
        )}
      </Section>
    </>
  )
}

export function MenuTab({ lead, menu }: { lead: LeadDetail; menu: Menu | null }) {
  const sections = arr(menu?.sections)
  const shots = lead.files.menu.filter((f) => f.is_image)
  return (
    <>
      <Section title="Menu" aside={sections.length ? `${sections.reduce((n, s) => n + arr(s.items).length, 0)} items in ${sections.length} sections` : undefined}>
        <Prose>{lead.profile?.menu_summary}</Prose>
        {sections.length === 0 ? (
          <p className="mt-2 text-muted-foreground">No menu was extracted. Add menu screenshots or a PDF under Materials and run the analysis again.</p>
        ) : (
          <div className="mt-4 columns-1 gap-8 lg:columns-2">
            {sections.map((s, i) => (
              <div key={i} className="mb-5 break-inside-avoid">
                <h3 className="border-b border-border pb-0.5 font-semibold">{s.name}</h3>
                <ul>
                  {arr(s.items).map((it, j) => (
                    <li key={j} className="flex items-baseline gap-3 border-b border-border/60 py-1">
                      <div className="min-w-0 flex-1">
                        <div>{it.name}</div>
                        {it.description ? <div className="text-xs text-muted-foreground">{it.description}</div> : null}
                      </div>
                      <div className="figure shrink-0">{cop(it.price_cop)}</div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
        {menu?.notes ? (
          <Sub title="Notes from the extraction">
            <Prose>{menu.notes}</Prose>
          </Sub>
        ) : null}
      </Section>
      {shots.length ? (
        <Section title="Menu files" aside={`${shots.length} added by hand`}>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {shots.map((f) => (
              <li key={f.name}>
                <a href={f.url} target="_blank" rel="noreferrer" className="block border border-border">
                  <img src={`${f.url}?w=640`} alt={`Menu file ${f.name}`} loading="lazy" className="w-full" />
                </a>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
    </>
  )
}

const SIGNAL_TONE = { open: "good", closed: "bad", unclear: "warn" } as const

export function PresenceTab({ presence }: { presence: Presence | null }) {
  if (!presence) {
    return (
      <Section title="Online presence">
        <p className="text-muted-foreground">The analysis did not include web research for this lead.</p>
      </Section>
    )
  }
  const platforms = arr(presence.platforms)
  const themes = presence.review_themes ?? {}
  const ig = presence.instagram ?? {}
  const signals = arr(presence.operating_signals)
  const v = presence.verdict ?? {}
  return (
    <>
      <Section title="Where they are found">
        {platforms.length ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[0.8125rem]">
              <thead>
                <tr className="text-left">
                  {["Platform", "Found", "Handle or link", "Rating", "Reviews", "Followers", "Last activity"].map((h) => (
                    <Lettering as="th" key={h} className="pr-3 pb-1 whitespace-nowrap">
                      {h}
                    </Lettering>
                  ))}
                </tr>
              </thead>
              <tbody>
                {platforms.map((p, i) => (
                  <tr key={i} className="border-t border-border align-top">
                    <td className="py-1.5 pr-3 font-medium whitespace-nowrap">{p.platform}</td>
                    <td className="py-1.5 pr-3">{p.found ? <Mark tone="good">Found</Mark> : <Mark>Not found</Mark>}</td>
                    <td className="max-w-56 py-1.5 pr-3 break-words">
                      {p.url ? <Ext href={p.url}>{p.handle || undefined}</Ext> : p.handle}
                      {p.notes ? <div className="text-xs text-muted-foreground">{p.notes}</div> : null}
                    </td>
                    <td className="figure py-1.5 pr-3">{p.rating ?? ""}</td>
                    <td className="figure py-1.5 pr-3">{p.review_count ?? ""}</td>
                    <td className="figure py-1.5 pr-3">{p.followers ?? ""}</td>
                    <td className="py-1.5 text-muted-foreground">{p.last_activity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Muted>No platforms recorded.</Muted>
        )}
        <Sub title="How it was confirmed to be this restaurant">
          <Prose>{presence.identity_check}</Prose>
        </Sub>
      </Section>

      <Section title="Operating signals">
        <div className="flex flex-wrap items-center gap-2">
          <VerdictMark verdict={v.status ?? "unknown"} />
          <LevelMark level={v.confidence} suffix=" confidence" />
        </div>
        <Prose className="mt-2">{v.reasoning}</Prose>
        {signals.length ? (
          <ul className="mt-3 flex flex-col">
            {signals.map((s, i) => (
              <li key={i} className="flex gap-3 border-t border-border py-2">
                <Mark tone={SIGNAL_TONE[s.direction ?? "unclear"] ?? "warn"} className="mt-0.5 shrink-0">
                  {s.direction ?? "unclear"}
                </Mark>
                <div className="min-w-0">
                  <div className="font-medium">{s.signal}</div>
                  <div className="prose-measure text-muted-foreground">{s.evidence}</div>
                  <div className="text-xs text-muted-foreground">
                    {s.date}
                    {s.date && s.source_url ? " · " : ""}
                    {s.source_url ? <Ext href={s.source_url}>source</Ext> : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </Section>

      <Section title="What reviewers say">
        {themes.recent_review_activity ? <Prose>{themes.recent_review_activity}</Prose> : null}
        <div className="mt-3 grid gap-6 sm:grid-cols-2">
          <Sub title="Praise" className="mt-0">
            <Bullets items={themes.praise} />
          </Sub>
          <Sub title="Complaints" className="mt-0">
            <Bullets items={themes.complaints} empty="None found." />
          </Sub>
        </div>
        {arr(themes.sample_quotes).length ? (
          <Sub title="In their words">
            <ul className="prose-measure flex flex-col gap-1.5">
              {arr(themes.sample_quotes).map((q, i) => (
                <li key={i} lang="es" className="border-l border-rule pl-3 italic">
                  {q}
                </li>
              ))}
            </ul>
          </Sub>
        ) : null}
      </Section>

      <Section title="Instagram">
        <Facts
          rows={[
            ["Handle", ig.handle],
            ["Followers", ig.followers?.toLocaleString("en")],
            ["Posting", ig.posting_frequency],
            ["Last post", ig.last_post],
            ["Content", ig.content_style],
          ]}
        />
      </Section>

      {arr(presence.recognition).length || arr(presence.promotions_or_events).length ? (
        <Section title="Recognition and events">
          <Bullets items={[...arr(presence.recognition), ...arr(presence.promotions_or_events)]} />
        </Section>
      ) : null}

      <Section title="Caveats">
        <Bullets items={presence.caveats} empty="None noted." />
        {arr(presence.sources).length ? (
          <Sub title="Sources seen">
            <ul className="flex flex-col gap-0.5 text-[0.8125rem]">
              {arr(presence.sources).slice(0, 40).map((s, i) => (
                <li key={i} className="truncate">
                  <Ext href={s.url}>{s.title || undefined}</Ext>
                </li>
              ))}
            </ul>
          </Sub>
        ) : null}
      </Section>
    </>
  )
}

const PRIORITY: Record<string, { text: string; tone: "ink" | "muted" | "outline" }> = {
  must: { text: "Must", tone: "ink" },
  should: { text: "Should", tone: "outline" },
  later: { text: "Later", tone: "muted" },
}

export function BuildPlanTab({ lead, profile }: { lead: LeadDetail; profile: Profile }) {
  const dev = profile.development_direction
  if (!dev) {
    return (
      <Section title="Build plan">
        <p className="text-muted-foreground">This profile was written before build plans were part of the analysis. Run the analysis again to get one.</p>
      </Section>
    )
  }
  const seo = dev.seo_plan ?? {}
  const out = dev.outreach ?? {}
  return (
    <>
      <Section
        title="Approach"
        aside={
          <DownloadLink
            href={`/api/leads/${lead.key}/build-plan.md`}
            title="A Markdown brief for a design agent: pages, features, menu, stack, SEO and phases. Leaves out the outreach notes."
          >
            Download brief (.md)
          </DownloadLink>
        }
      >
        <Prose>{dev.summary}</Prose>
        <div className="mt-4 grid gap-6 sm:grid-cols-2">
          <Sub title="Deliverables" className="mt-0">
            <Bullets items={dev.deliverables} />
          </Sub>
          <Sub title="Goals" className="mt-0">
            <Bullets items={dev.goals} />
          </Sub>
        </div>
      </Section>
      <Section title="Next steps">
        <Bullets items={dev.next_steps} ordered />
      </Section>
      <Section title="How to approach them">
        <Facts rows={[["Channels", arr(out.channels).length ? <Chips items={out.channels} /> : null], ["Timing", out.timing], ["Compliance", out.compliance]]} />
        <Sub title="Talking points">
          <Bullets items={out.talking_points} />
        </Sub>
        {arr(out.objections).length ? (
          <Sub title="Objections and answers">
            <dl className="prose-measure flex flex-col gap-2">
              {arr(out.objections).map((o, i) => (
                <div key={i}>
                  <dt className="font-medium">{o.objection}</dt>
                  <dd className="text-muted-foreground">{o.response}</dd>
                </div>
              ))}
            </dl>
          </Sub>
        ) : null}
      </Section>
      <Section title="Pages">
        <ul className="flex flex-col">
          {arr(dev.pages).map((p, i) => (
            <li key={i} className="border-t border-border py-2 first:border-0">
              <div className="font-medium">{p.name}</div>
              <div className="prose-measure text-muted-foreground">{p.purpose}</div>
              {arr(p.key_content).length ? <Bullets items={p.key_content} className="mt-1 text-[0.8125rem]" /> : null}
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Features">
        <ul className="flex flex-col">
          {arr(dev.features).map((f, i) => (
            <li key={i} className="flex gap-3 border-t border-border py-2 first:border-0">
              <Mark tone={PRIORITY[f.priority ?? "later"]?.tone ?? "muted"} className="mt-0.5 w-14 shrink-0 justify-center">
                {PRIORITY[f.priority ?? "later"]?.text ?? f.priority}
              </Mark>
              <div className="min-w-0">
                <div className="font-medium">{f.name}</div>
                <div className="prose-measure text-muted-foreground">{f.detail}</div>
              </div>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Menu system">
        <Prose>{dev.menu_system}</Prose>
      </Section>
      <Section title="Stack and hosting">
        <Facts rows={[...arr(dev.tech_stack).map((t): [string, ReactNode] => [t.layer ?? "", <><span className="font-medium">{t.choice}</span>{t.why ? <span className="text-muted-foreground"> · {t.why}</span> : null}</>]), ["Domain, hosting", dev.domain_and_hosting]]} />
        {arr(dev.integrations).length ? (
          <Sub title="Integrations">
            <Bullets items={dev.integrations} />
          </Sub>
        ) : null}
      </Section>
      <Section title="Local SEO">
        <Facts rows={[["Keywords", arr(seo.target_keywords).length ? <Chips items={seo.target_keywords} /> : null]]} />
        <div className="mt-4 grid gap-6 sm:grid-cols-3">
          <Sub title="On page" className="mt-0">
            <Bullets items={seo.on_page} />
          </Sub>
          <Sub title="Local" className="mt-0">
            <Bullets items={seo.local} />
          </Sub>
          <Sub title="Structured data" className="mt-0">
            <Bullets items={seo.structured_data} />
          </Sub>
        </div>
      </Section>
      <Section title="Phases">
        <ol className="flex flex-col">
          {arr(dev.phases).map((p, i) => (
            <li key={i} className="flex gap-3 border-t border-border py-2 first:border-0">
              <span className="lettering mt-0.5 grid size-5 shrink-0 place-items-center border border-rule" aria-label={`Size ${p.size ?? "unknown"}`}>
                {p.size ?? "?"}
              </span>
              <div className="min-w-0">
                <div className="font-medium">{p.name}</div>
                <Bullets items={p.tasks} className="mt-1" />
              </div>
            </li>
          ))}
        </ol>
      </Section>
      <Section title="Needed from the owner, and risks">
        <div className="grid gap-6 sm:grid-cols-2">
          <Sub title="Content needed" className="mt-0">
            <Bullets items={dev.content_needed} />
          </Sub>
          <Sub title="Risks" className="mt-0">
            <Bullets items={dev.risks} />
          </Sub>
        </div>
      </Section>
    </>
  )
}
