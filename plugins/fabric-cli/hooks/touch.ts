import type { TreeNode } from '../types'
import type { Invocation } from './parse'

export function fabTouched(inv: Invocation, nodes: TreeNode[]): string[] {
  const out = new Set<string>()
  for (const arg of inv.args.slice(1)) {
    if (!arg.includes('.') || /^(\.{1,2}\/|~)/.test(arg)) continue
    const want = arg.replace(/^\//, '').replace(/\/$/, '').toLowerCase()
    let best: TreeNode | undefined
    for (const n of nodes) {
      const have = n.path.toLowerCase()
      if (!have || (want !== have && !want.startsWith(`${have}/`))) continue
      if (!best || have.length > best.path.length) best = n
    }
    if (best) out.add(best.id)
  }
  return [...out]
}
