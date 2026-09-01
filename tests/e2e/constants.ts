export const bootstrapToken = 'researchpath-e2e-bootstrap-token-20260716'
export const previewSessionToken = 'researchpath-e2e-preview-session-token-20260716'

export function previewOrigin(): string {
  const port = Number.parseInt(
    process.env.RESEARCHPATH_E2E_PREVIEW_API_PORT ?? '19998',
    10,
  )
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new Error('RESEARCHPATH_E2E_PREVIEW_API_PORT 必须是 1—65535 的有效端口')
  }
  return `http://127.0.0.1:${port}`
}
