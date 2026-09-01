import { bootstrapToken } from './constants'

export default async function globalSetup(): Promise<void> {
  const apiPort = process.env.RESEARCHPATH_E2E_API_PORT ?? '19999'
  const response = await fetch(`http://127.0.0.1:${apiPort}/api/v1/session/bootstrap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bootstrapToken }),
  })
  if (!response.ok) {
    throw new Error(`E2E 会话初始化失败：HTTP ${response.status}`)
  }
  const payload = (await response.json()) as { token?: unknown }
  if (typeof payload.token !== 'string' || payload.token.length === 0) {
    throw new Error('E2E 会话初始化未返回可用令牌')
  }
  process.env.RESEARCHPATH_E2E_SESSION_TOKEN = payload.token
}
