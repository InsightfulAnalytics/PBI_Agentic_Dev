import type { TreeNode } from '../types'
import type { Invocation } from './parse'

const FOLDER_SEG = /\.folder$/i

function bare(path: string): string {
  return path
    .split('/')
    .filter(s => s && !FOLDER_SEG.test(s))
    .join('/')
}

export function nodeAtPath(nodes: TreeNode[], path: string): TreeNode | undefined {
  const want = path.replace(/^\/+|\/+$/g, '').toLowerCase()
  if (!want) return undefined
  const exact = nodes.find(n => n.path && n.path.toLowerCase() === want)
  if (exact || FOLDER_SEG.test(want)) return exact
  const flat = bare(want)
  return nodes.find(n => n.path && n.kind !== 'fabric folder' && bare(n.path.toLowerCase()) === flat)
}

export function fabTouched(inv: Invocation, nodes: TreeNode[]): string[] {
  const out = new Set<string>()
  for (const arg of inv.args.slice(1)) {
    if (!arg.includes('.') || /^(\.{1,2}\/|~)/.test(arg)) continue
    const segs = arg.replace(/^\/+|\/+$/g, '').split('/')
    for (let i = segs.length; i > 0; i--) {
      const n = nodeAtPath(nodes, segs.slice(0, i).join('/'))
      if (n) {
        out.add(n.id)
        break
      }
    }
  }
  return [...out]
}
