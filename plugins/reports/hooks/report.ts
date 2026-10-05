import type { TreeNode } from '../types'

type Json = Record<string, any>

const READS = 16

export type Io = {
  text: (path: string) => Promise<string>
  list: (path: string) => Promise<{ name: string; kind: string }[]>
  exists: (path: string) => Promise<boolean>
}

function node(id: string, parent: string, kind: string, name: string, path: string, sig = '', note = ''): TreeNode {
  return { id, parent, kind, name, path, hidden: false, sig, note }
}

function reason(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

function rel(base: string, path: string): string {
  return path.startsWith(base + '/') ? path.slice(base.length + 1) : path
}

async function json(io: Io, base: string, path: string): Promise<Json | null> {
  let text: string
  try {
    text = await io.text(path)
  } catch (err) {
    if (!(await io.exists(path))) return null
    throw new Error(`cannot read ${rel(base, path)}: ${reason(err)}`)
  }
  try {
    return JSON.parse(text) as Json
  } catch (err) {
    throw new Error(`invalid JSON in ${rel(base, path)}: ${reason(err)}`)
  }
}

async function entries(io: Io, base: string, path: string): Promise<{ name: string; kind: string }[]> {
  try {
    return await io.list(path)
  } catch (err) {
    if (!(await io.exists(path))) return []
    throw new Error(`cannot list ${rel(base, path)}: ${reason(err)}`)
  }
}

async function dirs(io: Io, base: string, path: string): Promise<string[]> {
  return (await entries(io, base, path)).filter(e => e.kind === 'dir').map(e => e.name)
}

async function each<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const out: R[] = []
  let next = 0
  const work = async () => {
    while (next < items.length) {
      const i = next++
      out[i] = await fn(items[i] as T)
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, work))
  return out
}

function hash(s: string): string {
  let x = 5381
  for (let i = 0; i < s.length; i++) x = (x * 33 + s.charCodeAt(i)) >>> 0
  return x.toString(16)
}

function fieldName(field: Json | undefined): string {
  if (!field) return '?'
  const inner = field.Column ?? field.Measure ?? field.Aggregation?.Expression?.Column ?? field.HierarchyLevel ?? {}
  const entity = inner.Expression?.SourceRef?.Entity ?? inner.Expression?.Hierarchy?.Expression?.SourceRef?.Entity ?? ''
  const prop = inner.Property ?? inner.Level ?? ''
  return entity ? `${entity}.${prop}` : prop || '?'
}

function filters(list: Json[] | undefined, parent: string, base: string, kind: string): TreeNode[] {
  if (!list?.length) return []
  const gid = `${parent}/filters`
  const out = [node(gid, parent, 'group', `Filters (${list.length})`, '')]
  for (const f of list) {
    const name = fieldName(f.field)
    out.push(node(`${gid}/${f.name}`, gid, kind, name, `${base}/${name}.Filter`, hash(JSON.stringify(f)), f.type ?? ''))
  }
  return out
}

function literal(v: Json | undefined): string {
  const s = v?.expr?.Literal?.Value
  return typeof s === 'string' ? s.replace(/^'|'$/g, '') : ''
}

export async function loadReport(io: Io, dir: string): Promise<TreeNode[]> {
  const def = `${dir}/definition`
  const report = await json(io, dir, `${def}/report.json`)
  if (!report) throw new Error(`not a PBIR report: ${dir}`)
  const rname = dir.split('/').pop() ?? 'Report'
  const root = 'R'
  const out: TreeNode[] = [node(root, '', 'report', rname, rname, hash(JSON.stringify(report)))]

  const pbir = await json(io, dir, `${dir}/definition.pbir`)
  const ref = pbir?.datasetReference ?? {}
  const byPath: string = ref.byPath?.path ?? ''
  const conn: string = ref.byConnection?.connectionString ?? ''
  const modelName = byPath
    ? (byPath.split(/[\\/]/).pop() ?? byPath).replace(/\.SemanticModel$/i, '')
    : (conn.match(/initial catalog=([^;"]+)/i)?.[1] ?? conn.match(/semanticmodelid=([^;"]+)/i)?.[1] ?? ref.byConnection?.pbiModelDatabaseName ?? '')
  if (modelName) {
    out.push(node(`${root}/model`, root, 'semantic model', modelName, '', hash(JSON.stringify(ref)), byPath ? 'local model' : 'live connection'))
  }
  const theme = report.themeCollection?.customTheme?.name ?? report.themeCollection?.baseTheme?.name
  if (theme) out.push(node(`${root}/theme`, root, 'theme', theme, `${rname}/${theme}.Theme`, hash(JSON.stringify(report.themeCollection))))
  out.push(...filters(report.filterConfig?.filters, root, rname, 'reportfilter'))

  const meta = await json(io, dir, `${def}/pages/pages.json`)
  const folders = await dirs(io, dir, `${def}/pages`)
  const order: string[] = meta?.pageOrder ?? folders
  const pagesId = `${root}/pages`
  out.push(node(pagesId, root, 'group', `Pages (${order.length})`, ''))
  for (const pf of order) {
    const page = await json(io, dir, `${def}/pages/${pf}/page.json`)
    if (!page) continue
    const pid = `${pagesId}/${pf}`
    const ppath = `${rname}/${page.displayName ?? pf}.Page`
    const active = meta?.activePageName === pf ? 'active' : ''
    const hidden = page.visibility === 'HiddenInViewMode'
    out.push({ ...node(pid, pagesId, 'page', page.displayName ?? pf, ppath, hash(JSON.stringify(page)), active), hidden })
    out.push(...filters(page.filterConfig?.filters, pid, ppath, 'pagefilter'))
    const vdir = `${def}/pages/${pf}/visuals`
    const vfolders = await dirs(io, dir, vdir)
    const visuals = await each(vfolders, READS, async vf => ({ vf, v: await json(io, dir, `${vdir}/${vf}/visual.json`) }))
    const vis: { z: number; n: TreeNode[] }[] = []
    for (const { vf, v } of visuals) {
      if (!v) continue
      const vid = `${pid}/${vf}`
      const type = v.visual?.visualType ?? (v.visualGroup ? 'group' : 'visual')
      const title = literal(v.visual?.visualContainerObjects?.title?.[0]?.properties?.text) || v.visualGroup?.displayName || ''
      const vpath = `${ppath}/${v.name ?? vf}.Visual`
      const nodes: TreeNode[] = [
        {
          ...node(vid, pid, 'visual', title ? `${title}` : type, vpath, hash(JSON.stringify(v)), title ? type : ''),
          hidden: v.isHidden === true,
        },
      ]
      for (const [role, st] of Object.entries((v.visual?.query?.queryState ?? {}) as Json)) {
        const rid = `${vid}/${role}`
        nodes.push(node(rid, vid, 'data role', role, ''))
        for (const p of (st as Json).projections ?? []) {
          const ref = p.queryRef ?? fieldName(p.field)
          nodes.push(node(`${rid}/${ref}`, rid, 'field', p.displayName ?? ref, vpath, '', p.displayName ? ref : ''))
        }
      }
      nodes.push(...filters(v.filterConfig?.filters, vid, vpath, 'visualfilter'))
      vis.push({ z: v.position?.z ?? 0, n: nodes })
    }
    vis.sort((a, b) => b.z - a.z)
    for (const one of vis) out.push(...one.n)
  }

  const bdir = `${def}/bookmarks`
  const files = (await entries(io, dir, bdir)).filter(e => e.name.endsWith('.bookmark.json'))
  if (files.length) {
    const bid = `${root}/bookmarks`
    out.push(node(bid, root, 'group', `Bookmarks (${files.length})`, ''))
    for (const f of files) {
      const b = await json(io, dir, `${bdir}/${f.name}`)
      out.push(node(`${bid}/${f.name}`, bid, 'bookmark', b?.displayName ?? f.name, `${rname}/bookmark:${b?.name ?? f.name.replace(/\.bookmark\.json$/, '')}`, hash(JSON.stringify(b))))
    }
  }

  const ext = await json(io, dir, `${def}/reportExtensions.json`)
  const measures = (ext?.entities ?? []).flatMap((e: Json) =>
    (e.measures ?? []).map((m: Json) => ({ table: e.name, m })),
  )
  if (measures.length) {
    const xid = `${root}/ext`
    out.push(node(xid, root, 'group', `Report measures (${measures.length})`, ''))
    for (const { table, m } of measures)
      out.push(node(`${xid}/${table}.${m.name}`, xid, 'ext measure', m.name, rname, hash(m.expression ?? ''), table))
  }
  return out
}

export function reportDetail(n: TreeNode): string[] {
  const lines = [`${n.kind} ${n.name}`]
  if (n.path) lines.push(`pbir path: ${n.path}`)
  if (n.note) lines.push(`note: ${n.note}`)
  return lines
}
