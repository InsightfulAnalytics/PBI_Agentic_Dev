import type { AppInfo } from '../types'
import { type Cli, portalUrl, yamlScalar } from './apps'

type Deployment = {
  fabricItemId: string
  fabricWorkspaceId: string
  hostingUrl: string
  fabricDeepLink: string
  deployedAt: string
}

const DEPLOYMENT_FIELDS = ['fabricItemId', 'fabricWorkspaceId', 'hostingUrl', 'fabricDeepLink', 'deployedAt'] as const

export function yamlName(yaml: string): string {
  return yamlScalar(yaml.match(/^name:(.*)$/m)?.[1] ?? '')
}

function deploymentsOf(text: string): { all: Deployment[]; error: string } {
  if (!text.trim()) return { all: [], error: '' }
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch (err) {
    return { all: [], error: `.deployments.json is not valid JSON: ${err instanceof Error ? err.message : String(err)}` }
  }
  const map = parsed && typeof parsed === 'object' ? (parsed as { deployments?: unknown }).deployments : undefined
  if (map === undefined) return { all: [], error: '' }
  if (!map || typeof map !== 'object' || Array.isArray(map)) return { all: [], error: '.deployments.json: "deployments" is not an object' }
  const bad: string[] = []
  const all: Deployment[] = []
  for (const [key, raw] of Object.entries(map)) {
    if (!raw || typeof raw !== 'object') {
      bad.push(key)
      continue
    }
    const d = raw as Record<string, unknown>
    const out = { fabricItemId: '', fabricWorkspaceId: '', hostingUrl: '', fabricDeepLink: '', deployedAt: '' }
    for (const f of DEPLOYMENT_FIELDS) {
      const v = d[f]
      if (typeof v === 'string') out[f] = v
      else if (v !== undefined && v !== null) bad.push(`${key}.${f}`)
    }
    all.push(out)
  }
  return { all, error: bad.length ? `.deployments.json: ${bad.join(', ')} ${bad.length === 1 ? 'is' : 'are'} not of the expected type` : '' }
}

export function fromRayfin(dir: string, yaml: string, deployments: string): AppInfo {
  const name = yamlName(yaml) || dir.split('/').pop() || dir
  const { all, error } = deploymentsOf(deployments)
  const best = all.filter(d => d.fabricItemId).sort((a, b) => b.deployedAt.localeCompare(a.deployedAt))[0]
  const workspace = best?.fabricWorkspaceId ?? ''
  const item = best?.fabricItemId ?? ''
  const deep = best?.fabricDeepLink ?? ''
  return {
    dir,
    name,
    title: name,
    cli: 'rayfin',
    workspace,
    item,
    portal: deep.startsWith('https://') ? deep : portalUrl(workspace, item),
    hosting: best?.hostingUrl ?? '',
    sources: [],
    error,
  }
}

export const rayfin: Cli = {
  name: 'rayfin',
  commands: ['rayfin'],
  packages: ['@microsoft/rayfin-cli'],
  mutating: ['init', 'new', 'create', 'link', 'up', 'deploy', 'env', 'functions', 'ai-files', 'skills', 'template', 'add', 'remove'],
  deploy: ['up'],
  marker: 'rayfin/rayfin.yml',
  inputs: ['rayfin/.deployments.json'],
  start: 'rayfin init',
  skills: [],
  read: async (dir, text) => fromRayfin(dir, await text('rayfin/rayfin.yml'), await text('rayfin/.deployments.json')),
}
