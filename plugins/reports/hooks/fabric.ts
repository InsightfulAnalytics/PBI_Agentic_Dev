const PORTAL = 'https://app.powerbi.com'
const GUID = /^[0-9a-f-]{36}$/i

export function workspaceUrl(wsId: string): string {
  return GUID.test(wsId) ? `${PORTAL}/groups/${wsId}` : ''
}

export function reportUrl(wsId: string, reportId: string): string {
  const ws = workspaceUrl(wsId)
  return ws && GUID.test(reportId) ? `${ws}/reports/${reportId}` : ws
}

export function idOf(stdout: string): string {
  const m = stdout.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i)
  return m?.[0] ?? ''
}
