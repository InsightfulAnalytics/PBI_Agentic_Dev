import type { TreeNode } from '../types'
import type { Invocation } from './parse'

function glob(pattern: string): RegExp {
  const esc = pattern
    .split(/(\*\*|\*|\?)/)
    .map(p => (p === '**' ? '.*' : p === '*' ? '[^/]*' : p === '?' ? '.' : p.replace(/[.+^${}()|[\]\\]/g, '\\$&')))
    .join('')
  return new RegExp(`(^|/)${esc}$`, 'i')
}

function pbirParts(arg: string): { page?: string; visual?: string; glob: boolean } | null {
  const trimmed = arg.replace(/(\.(Page|Visual))\.[A-Za-z].*$/, '$1')
  const segs = trimmed.split('/')
  const page = segs.find(s => s.endsWith('.Page'))?.replace(/\.Page$/, '')
  const visual = segs.find(s => s.endsWith('.Visual'))?.replace(/\.Visual$/, '')
  if (!page && !visual) return null
  return { page, visual, glob: /[*?]/.test(trimmed) }
}

function matches(name: string, pattern: string, isGlob: boolean): boolean {
  if (!isGlob) return name.toLowerCase() === pattern.toLowerCase()
  return glob(pattern.replace(/^\*\*\/?/, '')).test(name)
}

export function pbirTouched(inv: Invocation, nodes: TreeNode[]): string[] {
  const out = new Set<string>()
  const pages = nodes.filter(n => n.kind === 'page')
  const visuals = nodes.filter(n => n.kind === 'visual')
  for (const arg of inv.args.slice(1)) {
    const p = pbirParts(arg)
    if (!p) continue
    const hitPages = p.page
      ? pages.filter(n => {
          const folder = n.id.split('/').pop() ?? ''
          return matches(n.name, p.page ?? '', p.glob) || matches(folder, p.page ?? '', p.glob)
        })
      : []
    if (!p.visual) {
      for (const n of hitPages) out.add(n.id)
      continue
    }
    for (const v of visuals) {
      const vname = v.path.split('/').pop()?.replace(/\.Visual$/, '') ?? ''
      const folder = (v.id.split('/').pop() ?? '').replace(/-Visual$/, '')
      const type = v.note || v.name
      const inPage = !p.page || p.page === '**' || hitPages.some(pg => v.parent === pg.id)
      const named = matches(vname, p.visual, p.glob) || matches(folder, p.visual, p.glob)
      if (inPage && (named || (p.glob && matches(type, p.visual, true)))) out.add(v.id)
    }
  }
  return [...out]
}
