import type { TreeNode } from '../types'
import { visualLabel } from './icons'

type Json = Record<string, any>

const READS = 16

export type Io = {
  text: (path: string) => Promise<string>
  list: (path: string) => Promise<{ name: string; kind: string }[]>
  exists: (path: string) => Promise<boolean>
}

function node(id: string, parent: string, kind: string, name: string, path: string, sig = '', note = '', file = ''): TreeNode {
  return { id, parent, kind, name, path, hidden: false, sig, note, ...(file ? { file } : {}) }
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

function filters(list: Json[] | undefined, parent: string, base: string, kind: string, file: string): TreeNode[] {
  if (!list?.length) return []
  const gid = `${parent}/filters`
  const out = [node(gid, parent, 'group', `Filters (${list.length})`, '', '', '', file)]
  for (const f of list) {
    const name = fieldName(f.field)
    out.push(node(`${gid}/${f.name}`, gid, kind, name, `${base}/${name}.Filter`, hash(JSON.stringify(f)), f.type ?? '', file))
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
  const out: TreeNode[] = [node(root, '', 'report', rname, rname, hash(JSON.stringify(report)), '', `${def}/report.json`)]

  const pbir = await json(io, dir, `${dir}/definition.pbir`)
  const ref = pbir?.datasetReference ?? {}
  const byPath: string = ref.byPath?.path ?? ''
  const mref = modelRef(pbir)
  const modelName = mref.name || mref.id
  if (modelName) {
    out.push(node(`${root}/model`, root, 'semantic model', modelName, '', hash(JSON.stringify(ref)), byPath ? 'local model' : 'live connection', `${dir}/definition.pbir`))
  }
  const theme = report.themeCollection?.customTheme?.name ?? report.themeCollection?.baseTheme?.name
  if (theme) {
    const tfile = themeFile(dir, report)
    const tid = `${root}/theme`
    out.push(node(tid, root, 'theme', theme, `${rname}/${theme}.Theme`, hash(JSON.stringify(report.themeCollection)), report.themeCollection?.customTheme?.name ? 'custom theme' : 'base theme', tfile))
    out.push(...themeNodes(await json(io, dir, tfile).catch(() => null), tid, tfile))
  }
  out.push(...filters(report.filterConfig?.filters, root, rname, 'reportfilter', `${def}/report.json`))

  const meta = await json(io, dir, `${def}/pages/pages.json`)
  const folders = await dirs(io, dir, `${def}/pages`)
  const order: string[] = meta?.pageOrder ?? folders
  const pagesId = `${root}/pages`
  out.push(node(pagesId, root, 'group', `Pages (${order.length})`, '', '', '', meta ? `${def}/pages/pages.json` : `${def}/pages`))
  for (const pf of order) {
    const page = await json(io, dir, `${def}/pages/${pf}/page.json`)
    if (!page) continue
    const pid = `${pagesId}/${pf}`
    const ppath = `${rname}/${page.displayName ?? pf}.Page`
    const active = meta?.activePageName === pf ? 'active' : ''
    const hidden = page.visibility === 'HiddenInViewMode'
    const pfile = `${def}/pages/${pf}/page.json`
    out.push({ ...node(pid, pagesId, 'page', page.displayName ?? pf, ppath, hash(JSON.stringify(page)), active, pfile), hidden })
    out.push(...filters(page.filterConfig?.filters, pid, ppath, 'pagefilter', pfile))
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
      const vfile = `${vdir}/${vf}/visual.json`
      const nodes: TreeNode[] = [
        {
          ...node(vid, pid, 'visual', title ? `${title}` : type, vpath, hash(JSON.stringify(v)), title ? type : '', vfile),
          hidden: v.isHidden === true,
        },
      ]
      for (const [role, st] of Object.entries((v.visual?.query?.queryState ?? {}) as Json)) {
        const rid = `${vid}/${role}`
        nodes.push(node(rid, vid, 'data role', role, '', '', '', vfile))
        for (const p of (st as Json).projections ?? []) {
          const ref = p.queryRef ?? fieldName(p.field)
          nodes.push(node(`${rid}/${ref}`, rid, 'field', p.displayName ?? ref, vpath, '', p.displayName ? ref : '', vfile))
        }
      }
      nodes.push(...filters(v.filterConfig?.filters, vid, vpath, 'visualfilter', vfile))
      vis.push({ z: v.position?.z ?? 0, n: nodes })
    }
    vis.sort((a, b) => b.z - a.z)
    for (const one of vis) out.push(...one.n)
  }

  const bdir = `${def}/bookmarks`
  const files = (await entries(io, dir, bdir)).filter(e => e.name.endsWith('.bookmark.json'))
  if (files.length) {
    const bid = `${root}/bookmarks`
    out.push(node(bid, root, 'group', `Bookmarks (${files.length})`, '', '', '', bdir))
    for (const f of files) {
      const b = await json(io, dir, `${bdir}/${f.name}`)
      out.push(node(`${bid}/${f.name}`, bid, 'bookmark', b?.displayName ?? f.name, `${rname}/bookmark:${b?.name ?? f.name.replace(/\.bookmark\.json$/, '')}`, hash(JSON.stringify(b)), '', `${bdir}/${f.name}`))
    }
  }

  const ext = await json(io, dir, `${def}/reportExtensions.json`)
  const measures = (ext?.entities ?? []).flatMap((e: Json) =>
    (e.measures ?? []).map((m: Json) => ({ table: e.name, m })),
  )
  if (measures.length) {
    const xid = `${root}/ext`
    out.push(node(xid, root, 'group', `Report measures (${measures.length})`, '', '', '', `${def}/reportExtensions.json`))
    for (const { table, m } of measures)
      out.push(node(`${xid}/${table}.${m.name}`, xid, 'ext measure', m.name, rname, hash(m.expression ?? ''), table, `${def}/reportExtensions.json`))
  }
  return out
}

const HEX = /^#[0-9a-f]{3,8}$/i

export function colorOf(v: unknown): string {
  if (typeof v === 'string') return HEX.test(v.trim()) ? v.trim() : ''
  const c = (v as Json | null | undefined)?.solid?.color
  return typeof c === 'string' && HEX.test(c.trim()) ? c.trim() : ''
}

function shown(v: unknown): string {
  const c = colorOf(v)
  if (c) return c
  if (v === null || v === undefined) return 'null'
  if (typeof v !== 'object') return String(v)
  const text = JSON.stringify(v)
  return text.length > 60 ? text.slice(0, 59) + '…' : text
}

const PLURAL: Record<string, string> = { property: 'properties', class: 'classes' }

function plural(n: number, word: string): string {
  return `${n} ${n === 1 ? word : (PLURAL[word] ?? `${word}s`)}`
}

function themeProps(el: Json, parent: string, file: string): TreeNode[] {
  return Object.entries(el)
    .filter(([k]) => k !== '$id')
    .map(([k, v]) => node(`${parent}/${k}`, parent, 'theme prop', k, '', hash(JSON.stringify(v)), shown(v), file))
}

function themeNodes(t: Json | null, tid: string, file: string): TreeNode[] {
  if (!t || typeof t !== 'object') return []
  const out: TreeNode[] = []
  const data = (Array.isArray(t.dataColors) ? t.dataColors : []).filter((c: unknown): c is string => typeof c === 'string')
  const named = Object.entries(t).filter((e): e is [string, string] => e[0] !== 'name' && typeof e[1] === 'string' && HEX.test(e[1].trim()))
  if (data.length || named.length) {
    const cid = `${tid}/colors`
    out.push(node(cid, tid, 'theme colors', 'Colors', '', '', plural(data.length + named.length, 'color'), file))
    if (data.length) {
      const did = `${cid}/data`
      out.push(node(did, cid, 'theme data colors', 'Data colors', '', hash(JSON.stringify(data)), plural(data.length, 'color'), file))
      data.forEach((c: string, i: number) => out.push(node(`${did}/${i}`, did, 'theme color', `Color ${i + 1}`, '', hash(c), c, file)))
    }
    for (const [k, v] of named) out.push(node(`${cid}/${k}`, cid, 'theme color', k, '', hash(v), v.trim(), file))
  }
  const classes = t.textClasses && typeof t.textClasses === 'object' ? Object.entries(t.textClasses as Json) : []
  if (classes.length) {
    const xid = `${tid}/text`
    out.push(node(xid, tid, 'theme text', 'Text classes', '', '', plural(classes.length, 'class'), file))
    for (const [k, v] of classes) {
      const style = (v ?? {}) as Json
      const font = typeof style.fontFace === 'string' ? (style.fontFace.split(',')[0] ?? '').replace(/['"]/g, '').trim() : ''
      const note = [font, style.fontSize !== undefined ? `${style.fontSize}pt` : '', colorOf(style.color)].filter(Boolean).join(' ')
      out.push(node(`${xid}/${k}`, xid, 'text class', k, '', hash(JSON.stringify(v)), note, file))
    }
  }
  const styles = t.visualStyles && typeof t.visualStyles === 'object' ? Object.entries(t.visualStyles as Json) : []
  if (styles.length) {
    const sid = `${tid}/styles`
    out.push(node(sid, tid, 'theme styles', 'Visual styles', '', '', plural(styles.length, 'target'), file))
    for (const [vtype, states] of styles) {
      const vid = `${sid}/${vtype}`
      const byState = states && typeof states === 'object' ? Object.entries(states as Json) : []
      const cardsOf = (cards: unknown) => (cards && typeof cards === 'object' ? Object.entries(cards as Json) : [])
      const count = byState.reduce((n, [, cards]) => n + cardsOf(cards).length, 0)
      out.push(node(vid, sid, 'theme style', vtype === '*' ? 'All visuals' : vtype, '', hash(JSON.stringify(states)), vtype === '*' ? `* wildcard, ${plural(count, 'card')}` : plural(count, 'card'), file))
      for (const [state, cards] of byState) {
        const at = byState.length > 1 || state !== '*' ? `${vid}/${state}` : vid
        if (at !== vid) out.push(node(at, vid, 'theme state', state === '*' ? 'All states' : state, '', hash(JSON.stringify(cards)), state === '*' ? '* wildcard' : '', file))
        for (const [card, list] of cardsOf(cards)) {
          const kid = `${at}/${card}`
          const items = (Array.isArray(list) ? list : [list]).filter((x: unknown): x is Json => Boolean(x) && typeof x === 'object')
          const props = items.reduce((n: number, el: Json) => n + Object.keys(el).filter(k => k !== '$id').length, 0)
          out.push(node(kid, at, 'theme card', card === '*' ? 'All cards' : card, '', hash(JSON.stringify(list)), card === '*' ? `* wildcard, ${plural(props, 'property')}` : plural(props, 'property'), file))
          if (items.length === 1 && items[0] && !items[0].$id) out.push(...themeProps(items[0], kid, file))
          else
            items.forEach((el: Json, i: number) => {
              const eid = `${kid}/${i}`
              out.push(node(eid, kid, 'theme selector', typeof el.$id === 'string' ? el.$id : `#${i + 1}`, '', hash(JSON.stringify(el)), plural(Object.keys(el).filter(k => k !== '$id').length, 'property'), file))
              out.push(...themeProps(el, eid, file))
            })
        }
      }
    }
  }
  return out
}

const NOTE_LABEL: Record<string, string> = {
  theme: 'Type',
  'theme color': 'Color',
  'theme prop': 'Value',
  'text class': 'Style',
  'theme colors': 'Count',
  'theme data colors': 'Count',
  'theme text': 'Count',
  'theme styles': 'Count',
  'theme style': 'Cards',
  'theme state': 'State',
  'theme card': 'Properties',
  'theme selector': 'Properties',
  page: 'State',
  'semantic model': 'Connection',
  field: 'Field',
  reportfilter: 'Filter type',
  pagefilter: 'Filter type',
  visualfilter: 'Filter type',
  'ext measure': 'Table',
}

function themeFile(dir: string, report: Json): string {
  const custom = report.themeCollection?.customTheme
  const base = report.themeCollection?.baseTheme
  if (custom?.name) return `${dir}/StaticResources/${custom.type === 'SharedResources' ? 'SharedResources' : 'RegisteredResources'}/${custom.name}`
  if (base?.name) return `${dir}/StaticResources/SharedResources/BaseThemes/${base.name}.json`
  return `${dir}/definition/report.json`
}

export type ModelRef = { workspace: string; id: string; name: string; local: string }

export function modelRef(pbir: Json | null): ModelRef {
  const ref = pbir?.datasetReference ?? {}
  const local: string = ref.byPath?.path ?? ''
  const conn: string = ref.byConnection?.connectionString ?? ''
  const field = (key: string) => {
    const m = conn.match(new RegExp(`${key}=("([^"]*)"|[^;]*)`, 'i'))
    return (m?.[2] ?? m?.[1] ?? '').trim()
  }
  return {
    workspace: (field('data source').match(/\/myorg\/(.+)$/i)?.[1] ?? '').trim(),
    id: field('semanticmodelid') || (ref.byConnection?.pbiModelDatabaseName ?? ''),
    name: local ? (local.split(/[\\/]/).pop() ?? local).replace(/\.SemanticModel$/i, '') : field('initial catalog'),
    local,
  }
}

export function reportDetail(n: TreeNode, dir: string): string[] {
  const label = NOTE_LABEL[n.kind] ?? 'Note'
  return [
    `${n.kind} ${n.name}`,
    ...(n.kind === 'visual' ? [`Visual type: ${visualLabel(n.note || n.name)}`] : n.note ? [`${label}: ${n.note}`] : []),
    ...(n.path ? [`pbir path: ${n.path}`] : []),
    ...(n.file ? [`File: ${rel(dir, n.file)}`] : []),
    ...(n.hidden ? ['Hidden: yes'] : []),
  ]
}
