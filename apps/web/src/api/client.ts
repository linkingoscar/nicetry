export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function renderDetail(detail: unknown, status: number): string {
  if (Array.isArray(detail)) {
    return detail.map((entry) => {
      if (entry && typeof entry === 'object') {
        const record = entry as { loc?: unknown; msg?: unknown; message?: unknown }
        const message = typeof record.msg === 'string'
          ? record.msg
          : typeof record.message === 'string'
            ? record.message
            : null
        if (message) {
          const location = Array.isArray(record.loc)
            ? record.loc.filter((part): part is string | number => typeof part === 'string' || typeof part === 'number').join(' → ')
            : ''
          return location ? `${location}：${message}` : message
        }
      }
      return String(entry)
    }).join('；')
  }
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in detail) {
    const message = (detail as { message?: unknown }).message
    if (typeof message === 'string') return message
  }
  return `请求失败：HTTP ${status}`
}

const SESSION_STORAGE_KEY = 'researchpath.sessionToken'
let sessionToken: string | null = sessionStorage.getItem(SESSION_STORAGE_KEY)
let sessionRequest: Promise<string> | null = null

function consumeBootstrapToken(): string | null {
  const fragment = new URLSearchParams(window.location.hash.slice(1))
  const bootstrapToken = fragment.get('bootstrap')
  if (bootstrapToken) history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
  return bootstrapToken
}

let launchBootstrapToken = consumeBootstrapToken()

async function getSessionToken(refresh = false): Promise<string> {
  if (refresh) {
    sessionToken = null
    sessionStorage.removeItem(SESSION_STORAGE_KEY)
    sessionRequest = null
  }
  if (sessionToken) return sessionToken
  if (!sessionRequest) {
    const bootstrapToken = launchBootstrapToken
    launchBootstrapToken = null
    if (!bootstrapToken) {
      throw new ApiError('缺少一次性会话启动凭据，请关闭当前页面并双击“启动研径.cmd”重新启动', 403, null)
    }
    sessionRequest = fetch('/api/v1/session/bootstrap', {
      method: 'POST',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bootstrapToken }),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new ApiError(
            '无法建立本地 API 会话，请关闭当前页面并双击“启动研径.cmd”重新启动',
            response.status,
            null,
          )
        }
        const body = (await response.json()) as { token: string }
        sessionToken = body.token
        sessionStorage.setItem(SESSION_STORAGE_KEY, body.token)
        return body.token
      })
      .finally(() => {
        sessionRequest = null
      })
  }
  return sessionRequest
}

async function fetchWithSession(
  url: string,
  init: RequestInit | undefined,
  refresh = false,
): Promise<Response> {
  const headers = new Headers(init?.headers)
  headers.set('X-ResearchPath-Token', await getSessionToken(refresh))
  return fetch(url, { ...init, headers })
}

export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  let response = await fetchWithSession(url, init)
  if (response.status === 403) {
    response = await fetchWithSession(url, init, true)
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null
    const detail = body?.detail
    throw new ApiError(renderDetail(detail, response.status), response.status, detail)
  }
  return (await response.json()) as T
}

export async function downloadWithSession(url: string, filename: string): Promise<void> {
  const response = await fetchWithSession(url, undefined)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null
    const detail = body?.detail
    throw new ApiError(renderDetail(detail, response.status), response.status, detail)
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}
