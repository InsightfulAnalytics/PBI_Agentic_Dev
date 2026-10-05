export type Target = { kind: 'local'; path: string }

export type TreeNode = {
  id: string
  parent: string
  kind: string
  name: string
  path: string
  hidden: boolean
  sig: string
  note: string
}

export type Explorer = {
  target: Target | null
  changed: string[]
  expanded: string[]
  query: string
  cursor: string
  selected: string
  detail: string[]
  status: string
  flash: string[]
  flashDim: string[]
  work: { run: string; tone: string; running: boolean; at: number } | null
  targetUrl: string
  scroll: Record<string, number>
  root: string
}

export type Tree = {
  target: Target | null
  nodes: TreeNode[]
}

declare module 'claude-code' {
  interface PluginState {
    'reports': {
      explorer: Explorer
      tree: Tree
    }
  }
}
