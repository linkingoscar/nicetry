import { afterEach, describe, expect, it, vi } from 'vitest'

describe('getModelDraft', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    sessionStorage.removeItem('researchpath.sessionToken')
  })

  it('carries the session token on the draft GET request and tolerates null', async () => {
    sessionStorage.setItem('researchpath.sessionToken', 'test-token')
    vi.resetModules()
    const { getModelDraft } = await import('./models')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(null), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const draft = await getModelDraft('dataset_x', 'model_y')

    expect(draft).toBeNull()
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/datasets/dataset_x/models/model_y/draft')
    const headers = new Headers(init?.headers)
    expect(headers.get('X-ResearchPath-Token')).toBe('test-token')
  })
})
