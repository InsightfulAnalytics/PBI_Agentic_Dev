import type { TreeNode } from '../types'

export const PLACEHOLDER = 'placeholder'
const PORTAL = 'https://app.powerbi.com'

const ITEM_ROUTE: Record<string, string> = {
  Report: 'reports',
  SemanticModel: 'datasets',
  Dashboard: 'dashboards',
  PaginatedReport: 'rdlreports',
  Lakehouse: 'lakehouses',
  Warehouse: 'datawarehouses',
  Notebook: 'synapsenotebooks',
  DataPipeline: 'pipelines',
  Dataflow: 'dataflows-gen2',
  Eventhouse: 'eventhouses',
  KQLDatabase: 'databases',
  SQLDatabase: 'sqldatabases',
  Environment: 'sparkenvironments',
}

type Entry = { name: string; id: string; type?: string }

function node(id: string, parent: string, kind: string, name: string, path: string, url = ''): TreeNode {
  return { id, parent, kind, name, path, hidden: false, sig: '', note: '', url }
}

function stub(parent: string): TreeNode {
  return node(`${parent}/…`, parent, PLACEHOLDER, 'loading…', '')
}

function entries(stdout: string): Entry[] {
  const start = stdout.indexOf('{')
  if (start < 0) throw new Error('fab ls returned no JSON')
  const parsed = JSON.parse(stdout.slice(start)) as { result?: { data?: Entry[] } }
  if (!parsed.result || !Array.isArray(parsed.result.data ?? [])) throw new Error('fab ls returned an unexpected shape')
  return (parsed.result.data ?? []).filter(e => typeof e?.name === 'string')
}

function split(entry: string): { name: string; type: string } {
  const dot = entry.lastIndexOf('.')
  return dot > 0 ? { name: entry.slice(0, dot), type: entry.slice(dot + 1) } : { name: entry, type: '' }
}

export function workspaceUrl(wsId: string): string {
  return /^[0-9a-f-]{36}$/i.test(wsId) ? `${PORTAL}/groups/${wsId}` : ''
}

export function itemUrl(wsId: string, type: string, itemId: string): string {
  const ws = workspaceUrl(wsId)
  if (!ws || !/^[0-9a-f-]{36}$/i.test(itemId)) return ws
  const route = ITEM_ROUTE[type]
  if (!route) return ws
  return type === 'SemanticModel' ? `${ws}/${route}/${itemId}/details` : `${ws}/${route}/${itemId}`
}

export function parseWorkspaces(stdout: string): TreeNode[] {
  const out: TreeNode[] = []
  for (const e of entries(stdout)) {
    const { name, type } = split(e.name)
    if (type !== 'Workspace') continue
    const id = `W:${name}`
    out.push({ ...node(id, '', 'workspace', name, e.name, workspaceUrl(e.id)), sig: e.id }, stub(id))
  }
  return out
}

function wsIdOf(parent: TreeNode, nodes: TreeNode[]): string {
  let cur: TreeNode | undefined = parent
  while (cur && cur.kind !== 'workspace') cur = nodes.find(n => n.id === cur?.parent)
  return cur?.sig ?? ''
}

export function parseChildren(stdout: string, parent: TreeNode, nodes: TreeNode[]): TreeNode[] {
  const wsId = wsIdOf(parent, nodes)
  const out: TreeNode[] = []
  for (const e of entries(stdout)) {
    const { name, type } = split(e.name)
    if (!type) continue
    const id = `${parent.id}/${e.name}`
    const path = `${parent.path}/${e.name}`
    if (type === 'Folder') out.push({ ...node(id, parent.id, 'fabric folder', name, path, workspaceUrl(wsId)), sig: wsId }, stub(id))
    else if (ONELAKE_ITEMS.has(type)) out.push({ ...node(id, parent.id, type, name, path, itemUrl(wsId, type, e.id ?? '')), note: typeLabel(type) }, stub(id))
    else out.push({ ...node(id, parent.id, type, name, path, itemUrl(wsId, type, e.id ?? '')), note: typeLabel(type) })
  }
  return out
}

const ONELAKE_ITEMS = new Set(['Lakehouse'])
const ONELAKE_DIRS = new Set(['lakehouse folder', 'onelake folder', 'onelake dir', 'onelake schema'])

export function inOneLake(n: TreeNode): boolean {
  return ONELAKE_ITEMS.has(n.kind) || ONELAKE_DIRS.has(n.kind)
}

export function parseOneLake(stdout: string, parent: TreeNode): { kids: TreeNode[]; become: string } {
  const list = entries(stdout)
  const tables = /\.Lakehouse\/Tables(\/|$)/i.test(parent.path)
  if (tables && parent.kind === 'onelake dir' && list.some(e => e.name === '_delta_log')) return { kids: [], become: 'lakehouse table' }
  const schema = tables && parent.kind === 'onelake dir'
  const out: TreeNode[] = []
  for (const e of list) {
    const name = e.type === 'Shortcut' ? e.name.replace(/\.Shortcut$/, '') : e.name
    const id = `${parent.id}/${name}`
    const path = `${parent.path}/${name}`
    if (ONELAKE_ITEMS.has(parent.kind)) out.push(node(id, parent.id, 'lakehouse folder', name, path), stub(id))
    else if (e.type === 'Directory' && schema) out.push({ ...node(id, parent.id, 'lakehouse table', name, path), note: 'Delta table' })
    else if (e.type === 'Directory' && tables) out.push(node(id, parent.id, 'onelake dir', name, path), stub(id))
    else if (e.type === 'Directory') out.push(node(id, parent.id, 'onelake folder', name, path), stub(id))
    else out.push({ ...node(id, parent.id, e.type === 'Shortcut' ? 'onelake shortcut' : 'onelake file', name, path), note: e.type === 'Shortcut' ? 'Shortcut' : '' })
  }
  return { kids: out, become: schema ? 'onelake schema' : '' }
}

export function workspaceOf(path: string): string | null {
  const m = path.match(/^\/?([^/]+)\.Workspace(\/|$)/i)
  return m?.[1] ?? null
}

export function modelOf(n: TreeNode): { server: string; database: string } | null {
  if (n.kind !== 'SemanticModel') return null
  const server = workspaceOf(n.path)
  return server ? { server, database: n.name } : null
}

const TYPE_LABEL: Record<string, string> = {
  AppBackend: 'Fabric App',
  KQLDatabase: 'KQL Database',
  KQLQueryset: 'KQL Queryset',
  KQLDashboard: 'Real-Time Dashboard',
  MLExperiment: 'ML Experiment',
  MLModel: 'ML Model',
  SQLEndpoint: 'SQL Endpoint',
  SQLDatabase: 'SQL Database',
  RDLReport: 'Paginated Report',
  PaginatedReport: 'Paginated Report',
}

export function typeLabel(type: string): string {
  return TYPE_LABEL[type] ?? type.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
}
