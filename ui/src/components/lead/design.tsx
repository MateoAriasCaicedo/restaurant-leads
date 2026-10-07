// The design system for the lead's site. Every string here was written by a model: it is rendered as plain text, and a
// colour only becomes a swatch when it is a six-digit hex value.
import { DesignSystemButton } from "@/components/lead/enrich"
import { Bullets, Chips, DownloadLink, Facts, Muted, Prose, Section, Sub } from "@/components/lead/parts"
import { Lettering } from "@/components/plan"
import { label } from "@/lib/format"
import type { Job, LeadDetail, Meta } from "@/lib/types"

const arr = <T,>(v: T[] | undefined | null): T[] => (Array.isArray(v) ? v : [])
const txt = (v: unknown): string => (typeof v === "string" ? v : "")
const HEX6 = /^#[0-9a-fA-F]{6}$/
const TOKEN = /^[a-z][a-z0-9-]{0,29}$/
/** The Tailwind utility a token becomes (bg-charcoal, text-h1), or nothing when the name would not make a valid one. */
const utility = (prefix: string, name: unknown): string => (typeof name === "string" && TOKEN.test(name) ? `${prefix}-${name}` : "")

export function DesignSystemTab({ lead, meta, onStarted }: { lead: LeadDetail; meta?: Meta; onStarted: (job: Job) => void }) {
  const ds = lead.design_system
  if (!ds) {
    return (
      <Section title="Design system" aside={<DesignSystemButton lead={lead} meta={meta} onStarted={onStarted} />}>
        <p className="prose-measure text-muted-foreground">
          This lead has no design system yet. Research written before design systems existed does not include one; Claude can write it now from the profile, menu and photos already collected, without repeating the web research.
        </p>
      </Section>
    )
  }
  const colors = arr(ds.colors).filter((c) => HEX6.test(txt(c?.hex)))
  const fonts = arr(ds.fonts).filter((f) => txt(f?.family))
  const scale = arr(ds.type_scale).filter((t) => txt(t?.token))
  const spacing = ds.spacing ?? {}
  const shape = ds.shape ?? {}
  const imagery = ds.imagery ?? {}
  const components = arr(ds.components).filter((c) => txt(c?.name))
  const microcopy = arr(ds.microcopy).filter((m) => txt(m?.context) && txt(m?.text))
  return (
    <>
      <Section
        title="Concept"
        aside={
          <span className="flex flex-wrap justify-end gap-2">
            <DesignSystemButton lead={lead} meta={meta} onStarted={onStarted} again />
            <DownloadLink
              href={`/api/leads/${lead.key}/design-system.md`}
              title="A Markdown file for the agent that builds the site with Next.js and Tailwind: theme tokens, next/font setup and components with their classes. Use it together with the build plan brief."
            >
              Download design system (.md)
            </DownloadLink>
          </span>
        }
      >
        <Prose>{txt(ds.concept)}</Prose>
        <Sub title="Principles">
          <Bullets items={ds.principles} />
        </Sub>
      </Section>

      <Section title="Colour">
        {colors.length ? (
          <ul className="grid grid-cols-2 gap-x-4 gap-y-5 sm:grid-cols-3 lg:grid-cols-4">
            {colors.map((c, i) => (
              <li key={i} className="min-w-0">
                <div className="h-14 border border-rule" style={{ background: c.hex }} role="img" aria-label={`${txt(c.name) || "Colour"} ${c.hex}`} />
                <div className="mt-1 flex items-baseline justify-between gap-2">
                  <span className="truncate font-medium">{txt(c.name)}</span>
                  <span className="plot-no text-xs uppercase">{c.hex}</span>
                </div>
                {txt(c.role) ? <Lettering as="div">{label(txt(c.role))}</Lettering> : null}
                {utility("bg", c.name) ? <div className="font-mono text-xs">{utility("bg", c.name)}</div> : null}
                {txt(c.usage) ? <div className="text-xs text-muted-foreground">{txt(c.usage)}</div> : null}
              </li>
            ))}
          </ul>
        ) : (
          <Muted>Nothing recorded.</Muted>
        )}
      </Section>

      <Section title="Typography">
        {fonts.length ? (
          <ul className="flex flex-col">
            {fonts.map((f, i) => (
              <li key={i} className="flex gap-3 border-t border-border py-2 first:border-0">
                <Lettering className="mt-0.5 w-16 shrink-0">{txt(f.role) ? label(txt(f.role)) : "Font"}</Lettering>
                <div className="min-w-0">
                  <div>
                    <span className="font-medium">{txt(f.family)}</span>
                    {utility("font", f.role) ? <span className="font-mono text-xs"> · {utility("font", f.role)}</span> : null}
                    <span className="text-muted-foreground">
                      {[txt(f.kind), arr(f.weights).filter((w) => typeof w === "number").join(", ")].filter(Boolean).map((x) => ` · ${x}`).join("")}
                    </span>
                  </div>
                  {txt(f.why) ? <div className="prose-measure text-muted-foreground">{txt(f.why)}</div> : null}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <Muted>Nothing recorded.</Muted>
        )}
        {scale.length ? (
          <Sub title="Type scale">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[0.8125rem]">
                <thead>
                  <tr className="text-left">
                    {["Utility", "Size", "Line height", "Weight", "Use"].map((h) => (
                      <Lettering as="th" key={h} className="pr-3 pb-1 whitespace-nowrap">
                        {h}
                      </Lettering>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {scale.map((t, i) => (
                    <tr key={i} className="border-t border-border align-top">
                      <td className="py-1.5 pr-3 font-mono text-xs whitespace-nowrap">{utility("text", t.token) || txt(t.token)}</td>
                      <td className="figure py-1.5 pr-3 whitespace-nowrap">{txt(t.size)}</td>
                      <td className="figure py-1.5 pr-3">{txt(t.line_height)}</td>
                      <td className="figure py-1.5 pr-3">{typeof t.weight === "number" ? t.weight : ""}</td>
                      <td className="py-1.5 text-muted-foreground">{txt(t.usage)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Sub>
        ) : null}
      </Section>

      <Section title="Layout, shape and imagery">
        <Facts
          rows={[
            ["Content width", txt(spacing.max_width)],
            ["Spacing steps", arr(spacing.scale).filter(txt).length ? <Chips items={spacing.scale} /> : null],
            ["Corner radius", txt(shape.radius)],
            ["Borders", txt(shape.borders)],
            ["Shadows", txt(shape.shadows)],
            ["Aspect ratios", arr(imagery.aspect_ratios).filter(txt).length ? <Chips items={imagery.aspect_ratios} /> : null],
          ]}
        />
        {txt(spacing.layout) ? (
          <Sub title="Layout">
            <Prose>{txt(spacing.layout)}</Prose>
          </Sub>
        ) : null}
        {txt(imagery.treatment) || arr(imagery.guidelines).length ? (
          <Sub title="Photography">
            <Prose>{txt(imagery.treatment)}</Prose>
            {arr(imagery.guidelines).length ? <Bullets items={imagery.guidelines} className="mt-2" /> : null}
          </Sub>
        ) : null}
      </Section>

      <Section title="Components" aside={components.length ? `${components.length} described` : undefined}>
        {components.length ? (
          <ul className="flex flex-col">
            {components.map((c, i) => (
              <li key={i} className="border-t border-border py-2 first:border-0">
                <div className="font-medium">{txt(c.name)}</div>
                <div className="prose-measure text-muted-foreground">{txt(c.description)}</div>
                {arr(c.classes).filter((p) => txt(p?.part) && txt(p?.classes)).length ? (
                  <dl className="mt-1.5 flex flex-col gap-1">
                    {arr(c.classes)
                      .filter((p) => txt(p?.part) && txt(p?.classes))
                      .map((p, j) => (
                        <div key={j} className="flex gap-3">
                          <Lettering as="dt" className="w-16 shrink-0 pt-0.5">
                            {txt(p.part)}
                          </Lettering>
                          <dd className="min-w-0 font-mono text-xs break-words">{txt(p.classes)}</dd>
                        </div>
                      ))}
                  </dl>
                ) : null}
                {arr(c.states).filter(txt).length || arr(c.used_on).filter(txt).length ? (
                  <Facts
                    className="mt-1.5 text-[0.8125rem]"
                    rows={[
                      ["States", arr(c.states).filter(txt).length ? <Chips items={c.states} /> : null],
                      ["Used on", arr(c.used_on).filter(txt).length ? <Chips items={c.used_on} /> : null],
                    ]}
                  />
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <Muted>Nothing recorded.</Muted>
        )}
      </Section>

      <Section title="Motion and accessibility">
        <div className="grid gap-6 sm:grid-cols-2">
          <Sub title="Motion" className="mt-0">
            <Prose>{txt(ds.motion)}</Prose>
          </Sub>
          <Sub title="Accessibility" className="mt-0">
            <Bullets items={ds.accessibility} />
          </Sub>
        </div>
      </Section>

      <Section title="Voice and microcopy">
        {microcopy.length ? (
          <dl className="flex flex-col gap-1.5">
            {microcopy.map((m, i) => (
              <div key={i} className="flex gap-4">
                <Lettering as="dt" className="w-40 shrink-0 pt-0.5">
                  {txt(m.context)}
                </Lettering>
                <dd lang="es">{txt(m.text)}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <Muted>Nothing recorded.</Muted>
        )}
      </Section>

      <Section title="Do and don't">
        <div className="grid gap-6 sm:grid-cols-2">
          <Sub title="Do" className="mt-0">
            <Bullets items={ds.dos} />
          </Sub>
          <Sub title="Don't" className="mt-0">
            <Bullets items={ds.donts} />
          </Sub>
        </div>
      </Section>

      <Section title="Basis and confidence" aside="Colours read from photos are approximate">
        <Prose>{txt(ds.basis)}</Prose>
      </Section>
    </>
  )
}
