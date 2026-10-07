// Every state-changing request carries X-Leads-UI: the server refuses writes without it, which is what
// stops another site open in the browser from posting to this local API.

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function parse<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(res.status, data?.error ?? `The server answered ${res.status}.`)
  }
  return data as T
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, init)
  } catch {
    throw new ApiError(0, "The app's server is not responding. Start it with: python app.py")
  }
  return parse<T>(res)
}

export function fetcher<T>(url: string): Promise<T> {
  return request<T>(url)
}

export function send<T = { ok: true }>(method: "POST" | "PUT" | "PATCH" | "DELETE", url: string, body?: unknown) {
  return request<T>(url, {
    method,
    headers: { "X-Leads-UI": "1", ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
}

export function upload<T>(url: string, files: File[]) {
  const form = new FormData()
  for (const f of files) form.append("files", f)
  return request<T>(url, { method: "POST", headers: { "X-Leads-UI": "1" }, body: form })
}

export function message(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong."
}
