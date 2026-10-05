import type { Target } from '../types'

export type Invocation = { tool: string; bin: string; args: string[]; cwd: string; env: Record<string, string> }

const SEPARATORS = new Set(['&&', '||', ';', '|', '&', '\n', '(', ')', '`'])
const PREFIXES = new Set(['do', 'then', 'else', 'elif', 'if', '!', 'time', '{', 'env', 'command', 'builtin', 'exec', 'nohup', 'sudo', 'nice', 'xargs', 'uvx', 'pipx', 'timeout', 'while', 'until'])
const PREFIX_VALUED: Record<string, Set<string>> = {
  sudo: new Set(['-u', '-g', '-C', '-h', '-p', '-U', '-r', '-t', '-D']),
  timeout: new Set(['-k', '-s', '--kill-after', '--signal']),
  xargs: new Set(['-n', '-I', '-P', '-L', '-s', '-d', '-E', '-a']),
  env: new Set(['-u', '-C', '-S', '--unset', '--chdir']),
  nice: new Set(['-n']),
  exec: new Set(['-a']),
  uvx: new Set(['--from', '--with', '-p', '--python']),
  uv: new Set(['--from', '--with', '-p', '--python', '--project', '--directory']),
  pipx: new Set(['--spec', '--python']),
}
const MAX_CALLS = 50
const REDIRECT = /^(\d*>>?|\d*<|\d*>&\d*|&>>?)$/

let drives = false

export function useDrives(on: boolean): void {
  drives = on
}

export function posix(path: string): string {
  if (!drives) return path
  return path.replace(/\\/g, '/').replace(/^\/([A-Za-z])(\/|$)/, (_, d: string) => `${d.toUpperCase()}:/`)
}

export function isAbsolute(path: string): boolean {
  return path.startsWith('/') || (drives && /^[A-Za-z]:\//.test(path))
}

export function tokenize(command: string): string[] {
  const out: string[] = []
  let cur = ''
  let quote = ''
  let has = false
  for (let i = 0; i < command.length; i++) {
    const ch = command[i] ?? ''
    if (!quote && ch === '#' && !has && !cur) {
      while (i + 1 < command.length && command[i + 1] !== '\n') i++
      continue
    }
    if (quote) {
      if (ch === quote) quote = ''
      else if (ch === '\\' && quote === '"' && i + 1 < command.length) cur += command[++i] ?? ''
      else cur += ch
      continue
    }
    if (ch === '"' || ch === "'") {
      quote = ch
      has = true
    } else if (ch === '\\' && i + 1 < command.length) {
      cur += command[++i] ?? ''
      has = true
    } else if (ch === '\n') {
      if (has || cur) out.push(cur)
      cur = ''
      has = false
      out.push('\n')
    } else if (/\s/.test(ch)) {
      if (has || cur) out.push(cur)
      cur = ''
      has = false
    } else if (ch === '>' || ch === '<') {
      let op = /^\d+$/.test(cur) || (cur === '&' && !has) ? cur : ''
      if (!op && (has || cur)) out.push(cur)
      op += ch
      while (command[i + 1] === '>' || command[i + 1] === '&' || /\d/.test(command[i + 1] ?? '')) {
        if (command[i + 1] === '&' && op.endsWith('&')) break
        op += command[++i]
      }
      out.push(op)
      cur = ''
      has = false
    } else if (ch === '(' || ch === ')' || ch === '`') {
      if (has || cur) out.push(cur)
      cur = ''
      has = false
      out.push(ch)
    } else if (ch === ';' || ch === '|' || ch === '&') {
      if (ch === '&' && command[i + 1] === '>') {
        if (has || cur) out.push(cur)
        cur = '&'
        has = false
        continue
      }
      if (has || cur) out.push(cur)
      cur = ''
      has = false
      const two = command.slice(i, i + 2)
      if (two === '&&' || two === '||') {
        out.push(two)
        i++
      } else out.push(ch)
    } else {
      cur += ch
      has = true
    }
  }
  if (has || cur) out.push(cur)
  if (!quote) return out
  return command
    .split(/(&&|\|\||[;|\n])/)
    .flatMap(part => (/^(&&|\|\||[;|\n])$/.test(part) ? [part] : part.trim().split(/\s+/).filter(Boolean)))
}

export function join(base: string, raw: string): string {
  const path = posix(raw)
  if (isAbsolute(path)) return path
  if (path.startsWith('~/')) return path
  const parts = base.split('/')
  for (const seg of path.split('/')) {
    if (seg === '' || seg === '.') continue
    if (seg === '..') parts.pop()
    else parts.push(seg)
  }
  return parts.join('/') || '/'
}

function operators(line: string): { word: string; tabs: boolean; expand: boolean }[] {
  const found: { word: string; tabs: boolean; expand: boolean }[] = []
  const outer: boolean[] = []
  let single = false
  let double = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (single) {
      if (ch === "'") single = false
      continue
    }
    if (ch === '\\') {
      i++
      continue
    }
    if (ch === '$' && line[i + 1] === '(') {
      outer.push(double)
      double = false
      i++
      continue
    }
    if (ch === ')' && outer.length && !double) {
      double = outer.pop() ?? false
      continue
    }
    if (ch === '"') {
      double = !double
      continue
    }
    if (double) continue
    if (ch === "'") {
      single = true
      continue
    }
    if (ch === '#' && (i === 0 || /\s/.test(line[i - 1] ?? ''))) break
    if (ch === '<' && line[i + 1] === '<' && line[i + 2] !== '<') {
      const m = line.slice(i).match(/^<<(-?)\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\2/)
      if (m) {
        found.push({ word: m[3] ?? '', tabs: m[1] === '-', expand: !m[2] })
        i += m[0].length - 1
      }
    }
  }
  return found
}

function heredocless(command: string): string {
  const out: string[] = []
  const pending: { word: string; tabs: boolean; expand: boolean }[] = []
  for (const line of command.split('\n')) {
    const head = pending[0]
    if (head) {
      if ((head.tabs ? line.replace(/^\t+/, '') : line) === head.word) pending.shift()
      else if (head.expand) out.push(...substitutions(line))
      continue
    }
    out.push(line)
    pending.push(...operators(line))
  }
  return out.join('\n')
}

function substitutions(command: string): string[] {
  const out: string[] = []
  let single = false
  let double = false
  for (let i = 0; i < command.length; i++) {
    const ch = command[i]
    if (single) {
      if (ch === "'") single = false
      continue
    }
    if (ch === '\\') {
      i++
      continue
    }
    if (ch === "'" && !double) {
      single = true
      continue
    }
    if (ch === '"') {
      double = !double
      continue
    }
    if (ch === '#' && !double && (i === 0 || /\s/.test(command[i - 1] ?? ''))) {
      while (i + 1 < command.length && command[i + 1] !== '\n') i++
      continue
    }
    if (ch === '$' && command[i + 1] === '(') {
      let depth = 0
      for (let j = i + 1; j < command.length; j++) {
        if (command[j] === '(') depth++
        else if (command[j] === ')' && --depth === 0) {
          out.push(command.slice(i + 2, j))
          i = j
          break
        }
      }
      continue
    }
    if (ch === '`') {
      let j = i + 1
      while (j < command.length && command[j] !== '`') j += command[j] === '\\' ? 2 : 1
      if (j < command.length) out.push(command.slice(i + 1, j))
      i = j
    }
  }
  return out
}

function expand(args: string[], loops: { name: string; words: string[] }[]): string[][] {
  let out = [args]
  for (const { name, words } of loops) {
    if (!name) continue
    const source = `\\$\\{${name}\\}|\\$${name}(?![A-Za-z0-9_])`
    const used = new RegExp(source)
    const ref = new RegExp(source, 'g')
    if (!out.some(a => a.some(x => used.test(x)))) continue
    out = out.flatMap(a => words.map(w => a.map(x => x.replace(ref, w)))).slice(0, MAX_CALLS)
  }
  return out
}

function skipFlags(toks: string[], j: number, word: string): number {
  const valued = PREFIX_VALUED[word]
  while (j < toks.length && (toks[j] ?? '').startsWith('-') && !SEPARATORS.has(toks[j] ?? '')) j += valued?.has(toks[j] ?? '') ? 2 : 1
  return j
}

export function invocations(command: string, sessionCwd: string, base: Record<string, string> = {}, tools: readonly string[] = ['fab']): Invocation[] {
  const text = heredocless(command)
  const toks = tokenize(text)
  const found: Invocation[] = []
  const loops: { name: string; words: string[] }[] = []
  const exported: Record<string, string> = { ...base }
  let cwd = sessionCwd
  let start = true
  for (let i = 0; i < toks.length && found.length < MAX_CALLS; i++) {
    const t = toks[i] ?? ''
    if (SEPARATORS.has(t)) {
      start = true
      continue
    }
    if (!start) continue
    start = false
    const env: Record<string, string> = {}
    let j = i
    for (;;) {
      const tok = toks[j] ?? ''
      const assign = tok.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/s)
      const word = tok.split('/').pop() ?? ''
      if (assign) {
        env[assign[1] ?? ''] = assign[2] ?? ''
        j++
      } else if (word === 'uv' && toks[j + 1] === 'run') j = skipFlags(toks, j + 2, 'uv')
      else if (word === 'timeout') {
        j = skipFlags(toks, j + 1, word)
        if (/^\d/.test(toks[j] ?? '')) j++
      } else if (word === 'while' || word === 'until') {
        loops.push({ name: '', words: [] })
        j++
      } else if (word === 'command' && /^-[A-Za-z]*[vV]/.test(toks[j + 1] ?? '')) break
      else if (PREFIXES.has(word)) j = skipFlags(toks, j + 1, word)
      else break
    }
    const head = toks[j]?.split('/').pop()
    const dir = toks[j + 1]
    if (head === 'export') {
      for (let k = j + 1; k < toks.length && !SEPARATORS.has(toks[k] ?? ''); k++) {
        const m = (toks[k] ?? '').match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/s)
        if (m) exported[m[1] ?? ''] = m[2] ?? ''
      }
      continue
    }
    if (head === 'for' && toks[j + 2] === 'in' && /^[A-Za-z_][A-Za-z0-9_]*$/.test(dir ?? '')) {
      const words: string[] = []
      for (let k = j + 3; k < toks.length && !SEPARATORS.has(toks[k] ?? '') && toks[k] !== 'do'; k++) words.push(toks[k] ?? '')
      loops.push({ name: dir ?? '', words: words.slice(0, 20) })
      continue
    }
    if (head === 'for' || head === 'select') {
      loops.push({ name: '', words: [] })
      continue
    }
    if (head === 'done') {
      loops.pop()
      continue
    }
    if (head === 'cd' && dir && !SEPARATORS.has(dir)) {
      cwd = join(cwd, dir)
      continue
    }
    if (!head || !tools.includes(head)) continue
    const args: string[] = []
    let k = j + 1
    while (k < toks.length && !SEPARATORS.has(toks[k] ?? '')) {
      const tok = toks[k++] ?? ''
      if (REDIRECT.test(tok)) {
        if (!/&\d*$/.test(tok) || tok.startsWith('&')) k++
        continue
      }
      args.push(tok)
    }
    for (const each of expand(args, loops)) if (found.length < MAX_CALLS) found.push({ tool: head, bin: toks[j] ?? head, args: each, cwd, env: { ...exported, ...env } })
    i = k - 1
  }
  const keyOf = (inv: Invocation) => `${inv.args.join('\0')}\0${JSON.stringify(inv.env)}`
  const seen = new Set(found.map(keyOf))
  for (const body of substitutions(text)) {
    for (const inv of invocations(body, cwd, exported, tools)) {
      const key = keyOf(inv)
      if (seen.has(key) || found.length >= MAX_CALLS) continue
      seen.add(key)
      found.push(inv)
    }
  }
  return found
}

export function targetLabel(t: Target | null): string {
  return t ? 'Fabric tenant' : 'no target'
}

export function fabWorkspaces(inv: Invocation): string[] {
  const out: string[] = []
  for (const a of inv.args.slice(1)) {
    const m = a.match(/^\/?([^/]+)\.Workspace(\/|$)/i)
    if (m?.[1]) out.push(m[1])
  }
  return out
}

export type FabKind = 'read' | 'download' | 'upload' | 'modify'

const FAB_READ = new Set(['ls', 'dir', 'get', 'exists', 'find', 'open', 'pwd', 'cd'])
const FAB_IGNORE = new Set(['auth', 'config', 'help', 'version', 'desc', '--help', '--version', '-h', '-v'])
const FAB_SUB_READ = new Set(['ls', 'list', 'get', 'run-list', 'run-status', 'schema', 'status'])
const FAB_VALUE_FLAGS = new Set(['-X', '--method', '-H', '--headers', '-i', '--input', '-A', '--audience', '-q', '--query', '-P', '--params', '-o', '--output', '--format'])
const ITEM_SUFFIX = /\.(Workspace|Capacity|Connection|Gateway|Domain|Lakehouse|Warehouse|SemanticModel|Report|Notebook|DataPipeline|Dataflow|Environment|KQLDatabase|Eventhouse|SQLDatabase|MirroredDatabase|SparkJobDefinition|PaginatedReport|Dashboard|AppBackend|UserDataFunction|Folder)(\/|$)/i

export function fabPositionals(args: string[]): string[] {
  const out: string[] = []
  for (let i = 0; i < args.length; i++) {
    const a = args[i] ?? ''
    if (a.startsWith('-')) {
      if (FAB_VALUE_FLAGS.has(a)) i++
      continue
    }
    out.push(a)
  }
  return out
}

function isLocal(arg: string): boolean {
  return /^(\.{1,2}\/|~|\/(?!.*\.Workspace))/.test(arg) || !ITEM_SUFFIX.test(arg)
}

export function fabKind(inv: Invocation): FabKind {
  const verb = inv.args[0] ?? ''
  const rest = inv.args.slice(1)
  const pos = fabPositionals(rest)
  if (verb === 'export' || verb === 'bulk-export') return 'download'
  if (verb === 'import' || verb === 'deploy' || verb === 'publish') return 'upload'
  if (verb === 'cp' || verb === 'copy') {
    const src = pos[0] ?? ''
    const dst = pos[pos.length - 1] ?? ''
    if (!isLocal(src) && isLocal(dst)) return 'download'
    if (isLocal(src) && !isLocal(dst)) return 'upload'
    return 'modify'
  }
  if (verb === 'api') {
    const eq = rest.find(a => a.startsWith('--method='))?.split('=')[1]
    const at = rest.findIndex(a => a === '-X' || a === '--method')
    const method = (eq ?? (at >= 0 ? rest[at + 1] : undefined) ?? 'get').toLowerCase()
    const url = pos[0] ?? ''
    if (/executeQueries|executeDaxQueries/i.test(url)) return 'read'
    if (/getdefinition/i.test(url)) return 'download'
    if (/updatedefinition/i.test(url)) return 'upload'
    return method === 'get' ? 'read' : 'modify'
  }
  if (verb === 'get' && rest.some(a => a === '-o' || a === '--output')) return 'download'
  if (verb === 'acl' || verb === 'label' || verb === 'job' || verb === 'table') return FAB_SUB_READ.has(pos[0] ?? '') ? 'read' : 'modify'
  return FAB_READ.has(verb) ? 'read' : 'modify'
}

export const FAB_TONE: Record<FabKind, string> = { read: 'purple', download: 'teal', upload: 'pink', modify: 'orange' }

function fabCd(cwd: string, target: string | undefined): string {
  if (!target || target === '~' || target === '/') return ''
  const parts = target.startsWith('/') ? [] : cwd.split('/').filter(Boolean)
  for (const seg of target.split('/')) {
    if (!seg || seg === '.') continue
    if (seg === '..') parts.pop()
    else parts.push(seg)
  }
  return parts.join('/')
}

export function fabCalls(calls: Invocation[]): Invocation[] {
  let cwd = ''
  const out: Invocation[] = []
  for (const inv of calls) {
    const verb = inv.args[0] ?? ''
    if (!verb || FAB_IGNORE.has(verb)) continue
    const args = cwd
      ? inv.args.map((a, i) => (i > 0 && !a.startsWith('-') && !a.startsWith('/') && ITEM_SUFFIX.test(a) && !/^[^/]+\.Workspace(\/|$)/i.test(a) && !isLocalPath(a) ? `${cwd}/${a}` : a))
      : inv.args
    if (verb === 'cd') cwd = fabCd(cwd, fabPositionals(inv.args.slice(1))[0])
    out.push({ ...inv, args })
  }
  return out
}

function isLocalPath(arg: string): boolean {
  return /^(\.{1,2}\/|~)/.test(arg)
}

const GUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi

export function fabGuids(inv: Invocation): string[] {
  return inv.args[0] === 'api' ? inv.args.slice(1).flatMap(a => a.match(GUID) ?? []).map(g => g.toLowerCase()) : []
}

function flagOf(args: string[], names: string[]): string {
  for (let i = 0; i < args.length; i++) {
    const a = args[i] ?? ''
    for (const n of names) {
      if (a === n) return args[i + 1] ?? ''
      if (a.startsWith(`${n}=`)) return a.slice(n.length + 1)
    }
  }
  return ''
}

export function decoded(text: string): string {
  try {
    return decodeURIComponent(text)
  } catch {
    return text
  }
}

export type Query = { workspace: string; model: string; database: string; report: string }

export function queryOf(inv: Invocation): Query | null {
  const none = { workspace: '', model: '', database: '', report: '' }
  if (inv.tool === 'te' && inv.args[0] === 'query') {
    const server = flagOf(inv.args, ['-s', '--server'])
    const ws = server.match(/^powerbi:\/\/[^/]+\/v1\.0\/[^/]+\/(.+)$/i)?.[1]
    const model = flagOf(inv.args, ['-d', '--database'])
    return ws && model ? { ...none, workspace: decoded(ws), model } : null
  }
  if (inv.tool === 'pbir' && inv.args[0] === 'model' && inv.args.some(a => a === '-q' || a === '--query' || a.startsWith('--query='))) {
    const report = inv.args[1] ?? ''
    return report && !report.startsWith('-') ? { ...none, report } : null
  }
  if (inv.tool === 'sqlcmd') {
    const database = flagOf(inv.args, ['-d', '--database-name'])
    return database ? { ...none, database } : null
  }
  return null
}

export function modelFromConnection(text: string): { workspace: string; model: string } | null {
  const m = text.match(/Data Source=\\?"?powerbi:\/\/[^/]+\/v1\.0\/[^/]+\/([^";\\]+)\\?"?;\s*initial catalog=\\?"?([^";\\]+)/i)
  return m?.[1] && m[2] ? { workspace: decoded(m[1].trim()), model: m[2].trim() } : null
}
