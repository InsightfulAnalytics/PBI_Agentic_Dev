export type FileNode = {
  id: string
  parent: string
  name: string
  kind: 'dir' | 'file' | 'link'
  hidden: boolean
  mtime: number
  loaded: boolean
}

export type Source = {
  kind: string
  name: string
  note: string
  item?: string
  children?: string[]
}

export type AppInfo = {
  dir: string
  name: string
  title: string
  cli: string
  workspace: string
  item: string
  portal: string
  hosting: string
  sources: Source[]
  error: string
}

export type FileTree = {
  root: string
  nodes: FileNode[]
  expanded: string[]
  cursor: string
  selected: string
  query: string
  showHidden: boolean
  git: Record<string, string>
  ignored: string[]
  untrackedDirs: string[]
  diff: Record<string, [number, number]>
  counts: Record<string, [number, number, number]>
  status: string
  flash: string[]
  flashDim: string[]
  flashOn: boolean
  flashTones: Record<string, string>
  scroll: number | null
  top: string
  work: { tone: string; n: number; at: number; until: number; lit: string[]; dim: string[] } | null
}

export type Theme = {
  fg: string
  accent: string
  muted: string
  urgent: string
  selection: string
}

declare module 'claude-code' {
  interface PluginState {
    'fabric-data-app': {
      tree: FileTree
      apps: AppInfo[]
      theme: Theme
    }
  }
}
