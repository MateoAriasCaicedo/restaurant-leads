import { Trash2Icon } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"
import { mutate } from "swr"

import { Muted } from "@/components/lead/parts"
import { Ext, Lettering, Mark } from "@/components/plan"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { keys } from "@/hooks/use-data"
import { message, send } from "@/lib/api"
import { ago, dateTime, googleMaps, googleSearch, host, label, withScheme } from "@/lib/format"
import type { LeadDetail, Meta } from "@/lib/types"

const OUTCOME_TONE: Record<string, "good" | "warn" | "bad" | "muted" | "outline"> = {
  no_answer: "muted",
  talking: "outline",
  interested: "good",
  meeting: "good",
  proposal_sent: "good",
  won: "good",
  not_interested: "warn",
  opt_out: "bad",
}

export function ContactCard({ lead }: { lead: LeadDetail }) {
  const p = lead.place
  const phones = (p.phone ?? "").split(";").map((x) => x.trim()).filter(Boolean)
  const site = p.website ? withScheme(p.website) : null
  const wa = lead.tags["contact:whatsapp"]
  const email = lead.tags.email ?? lead.tags["contact:email"]
  return (
    <section aria-labelledby="contact-h">
      <h2 id="contact-h" className="border-b border-rule pb-1 text-base font-semibold">
        Contact
      </h2>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
        <Lettering as="dt" className="pt-0.5">Phone</Lettering>
        <dd>
          {phones.length ? (
            phones.map((n) => (
              <a key={n} href={`tel:${n.replace(/[^\d+]/g, "")}`} className="figure mr-2 underline decoration-border hover:decoration-foreground">
                {n}
              </a>
            ))
          ) : (
            <Muted>None in the map data</Muted>
          )}
        </dd>
        {wa ? (
          <>
            <Lettering as="dt" className="pt-0.5">WhatsApp</Lettering>
            <dd className="figure">{wa}</dd>
          </>
        ) : null}
        {email ? (
          <>
            <Lettering as="dt" className="pt-0.5">Email</Lettering>
            <dd className="break-all">{email}</dd>
          </>
        ) : null}
        <Lettering as="dt" className="pt-0.5">Address</Lettering>
        <dd>{p.address || <Muted>None in the map data</Muted>}</dd>
        <Lettering as="dt" className="pt-0.5">Listed web</Lettering>
        <dd className="min-w-0 truncate">{site ? <Ext href={site}>{host(site) || p.website}</Ext> : <Muted>None</Muted>}</dd>
        <Lettering as="dt" className="pt-0.5">Verify</Lettering>
        <dd className="flex flex-wrap gap-x-3">
          <Ext href={googleSearch(p.name, p.area)}>Google</Ext>
          <Ext href={googleMaps(p.name, p.lat, p.lng)}>Maps</Ext>
          {p.maps_url ? <Ext href={p.maps_url}>OpenStreetMap</Ext> : null}
        </dd>
      </dl>
      <p className="mt-2 text-xs text-muted-foreground">Confirm details by phone before publishing anything: sources disagree.</p>
    </section>
  )
}

export function PrivateNote({ lead }: { lead: LeadDetail }) {
  const [text, setText] = useState(lead.private_note.body)
  const [saving, setSaving] = useState(false)
  const dirty = text !== lead.private_note.body

  async function save() {
    if (!dirty) return
    setSaving(true)
    try {
      await send("PUT", `/api/leads/${lead.key}/private-note`, { body: text })
      await mutate(keys.lead(lead.key))
    } catch (err) {
      toast.error(message(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section>
      <Field>
        <FieldLabel htmlFor="private-note" className="border-b border-rule pb-1 text-base font-semibold">
          Private note
        </FieldLabel>
        <Textarea id="private-note" value={text} onChange={(e) => setText(e.target.value)} onBlur={save} rows={4} placeholder="Who you spoke to, when to call back, what they said." />
        <FieldDescription>
          {saving ? "Saving" : dirty ? "Saves when you leave the field." : lead.private_note.updated_at ? `Saved ${ago(lead.private_note.updated_at)}. Never shown to the analysis.` : "Only you see this. It is never shown to the analysis."}
        </FieldDescription>
      </Field>
    </section>
  )
}

export function ContactLog({ lead, meta }: { lead: LeadDetail; meta?: Meta }) {
  const channels = meta?.channels ?? []
  const outcomes = meta?.outcomes ?? []
  const [channel, setChannel] = useState("whatsapp")
  const [outcome, setOutcome] = useState("no_answer")
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)

  async function add() {
    setBusy(true)
    try {
      await send("POST", `/api/leads/${lead.key}/contacts`, { channel, outcome, note })
      setNote("")
      await Promise.all([mutate(keys.lead(lead.key)), mutate(keys.leads)])
    } catch (err) {
      toast.error(message(err))
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: number) {
    try {
      await send("DELETE", `/api/contacts/${id}`)
      await Promise.all([mutate(keys.lead(lead.key)), mutate(keys.leads)])
    } catch (err) {
      toast.error(message(err))
    }
  }

  return (
    <section aria-labelledby="log-h">
      <h2 id="log-h" className="border-b border-rule pb-1 text-base font-semibold">
        Contact log
      </h2>
      <FieldGroup className="mt-2 gap-2">
        <div className="grid grid-cols-2 gap-2">
          <Field>
            <FieldLabel htmlFor="log-channel">Channel</FieldLabel>
            <Select value={channel} onValueChange={(v) => setChannel(v as string)} items={channels.map((c) => ({ value: c, label: label(c) }))}>
              <SelectTrigger id="log-channel" size="sm" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {channels.map((c) => (
                    <SelectItem key={c} value={c}>
                      {label(c)}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>
          <Field>
            <FieldLabel htmlFor="log-outcome">Outcome</FieldLabel>
            <Select value={outcome} onValueChange={(v) => setOutcome(v as string)} items={outcomes.map((c) => ({ value: c, label: label(c) }))}>
              <SelectTrigger id="log-outcome" size="sm" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {outcomes.map((c) => (
                    <SelectItem key={c} value={c}>
                      {label(c)}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>
        </div>
        <Field>
          <FieldLabel htmlFor="log-note">What happened</FieldLabel>
          <Textarea id="log-note" value={note} onChange={(e) => setNote(e.target.value)} rows={2} />
          {outcome === "opt_out" ? <FieldDescription className="text-bad">An opt-out marks the lead rejected. Do not contact them again (Ley 1581).</FieldDescription> : null}
        </Field>
        <div>
          <Button size="sm" onClick={add} disabled={busy}>
            {busy ? <Spinner data-icon="inline-start" /> : null}
            Log contact
          </Button>
        </div>
      </FieldGroup>

      {lead.contacts.length ? (
        <ol className="mt-4 flex flex-col">
          {lead.contacts.map((c) => (
            <li key={c.id} className="group border-t border-border py-2">
              <div className="flex items-center gap-2">
                <Mark tone={OUTCOME_TONE[c.outcome] ?? "muted"}>{label(c.outcome)}</Mark>
                <span className="text-[0.8125rem]">{label(c.channel)}</span>
                <span className="figure ml-auto text-xs text-muted-foreground" title={dateTime(c.at)}>
                  {ago(c.at)}
                </span>
                <Button variant="ghost" size="icon-xs" onClick={() => void remove(c.id)} aria-label="Delete this entry" className="opacity-0 group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100">
                  <Trash2Icon />
                </Button>
              </div>
              {c.note ? <p className="mt-1 whitespace-pre-line">{c.note}</p> : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 text-[0.8125rem] text-muted-foreground">No contact logged. Logging one marks the lead as contacted.</p>
      )}
    </section>
  )
}
