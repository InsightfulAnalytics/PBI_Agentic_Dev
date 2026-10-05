export type Target = { kind: 'fabric'; identity?: string }

export type TreeNode = {
  id: string
  parent: string
  kind: string
  name: string
  path: string
  hidden: boolean
  sig: string
  note: string
  url?: string
}

export type SetupKind = 'missing' | 'signed-out' | 'unreachable'

export type Setup = { kind: SetupKind; line: string }

export type Work = { tone: string; at: number }

export type Explorer = {
  target: Target | null
  nodes: TreeNode[]
  expanded: string[]
  query: string
  cursor: string
  selected: string
  detail: string[]
  status: string
  flash: string[]
  work: Work | null
  busy: Record<string, { tone: string; n: number; at: number }>
  flashDim: string[]
  scroll: number | null
  root: string
  setup: Setup | null
  byDomain?: boolean
}

declare module 'claude-code' {
  interface PluginState {
    'fabric-cli': {
      explorer: Explorer
      nodes: TreeNode[]
    }
  }
}
