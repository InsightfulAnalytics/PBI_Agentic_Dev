import type { Explorer, TreeNode } from '../types'

export type Row = { node: TreeNode; depth: number; open: boolean; leaf: boolean }

export function empty(): Explorer {
  return {
    target: null,
    changed: [],
    expanded: [],
    query: '',
    cursor: '',
    selected: '',
    detail: [],
    status: '',
    flash: [],
    flashDim: [],
    work: null,
    targetUrl: '',
    scroll: {},
    root: '',
  }
}

export function diff(before: TreeNode[], after: TreeNode[]): string[] {
  if (before.length === 0) return []
  const old = new Map(before.map(n => [n.id, n.sig + '|' + n.hidden]))
  const out = new Set(after.filter(n => old.get(n.id) !== n.sig + '|' + n.hidden).map(n => n.id))
  const was = new Map(before.map(n => [n.id, n]))
  const now = new Map(after.map(n => [n.id, n]))
  for (const n of before) {
    if (now.has(n.id)) continue
    let up = was.get(n.parent)
    while (up && !now.has(up.id)) up = was.get(up.parent)
    if (up) out.add(up.id)
  }
  return [...out]
}

function childrenOf(nodes: TreeNode[]): Map<string, TreeNode[]> {
  const kids = new Map<string, TreeNode[]>()
  for (const n of nodes) {
    const list = kids.get(n.parent)
    if (list) list.push(n)
    else kids.set(n.parent, [n])
  }
  return kids
}

export function ancestors(nodes: TreeNode[], id: string, byId?: Map<string, TreeNode>): string[] {
  const map = byId ?? new Map(nodes.map(n => [n.id, n]))
  const out: string[] = []
  let cur = map.get(id)
  while (cur && cur.parent) {
    out.push(cur.parent)
    cur = map.get(cur.parent)
  }
  return out
}

export function visible(ex: Explorer, nodes: TreeNode[], root = ''): Row[] {
  const kids = childrenOf(nodes)
  const q = ex.query.trim().toLowerCase()
  let keep: Set<string> | null = null
  if (q) {
    keep = new Set()
    const byId = new Map(nodes.map(n => [n.id, n]))
    for (const n of nodes) {
      if (!n.name.toLowerCase().includes(q) && !n.note.toLowerCase().includes(q)) continue
      let cur: TreeNode | undefined = n
      while (cur && !keep.has(cur.id)) {
        keep.add(cur.id)
        cur = byId.get(cur.parent)
      }
    }
  }
  const open = new Set(ex.expanded)
  const rows: Row[] = []
  const walk = (parent: string, depth: number) => {
    for (const n of kids.get(parent) ?? []) {
      if (keep && !keep.has(n.id)) continue
      const leaf = !kids.has(n.id)
      const isOpen = !leaf && (keep ? true : open.has(n.id))
      rows.push({ node: n, depth, open: isOpen, leaf })
      if (isOpen) walk(n.id, depth + 1)
    }
  }
  walk(root, 0)
  return rows
}
