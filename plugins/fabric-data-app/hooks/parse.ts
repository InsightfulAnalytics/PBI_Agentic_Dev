import type { Cli } from './apps'
import { CLIS } from './clis'
import { isAbsolute, posix, resolvePath } from './tree'

export type Invocation = { head: string; args: string[]; cwd: string }
export type CliCall = { cli: Cli; args: string[]; cwd: string }

const SEPARATORS = new Set(['&&', '||', ';', '|', '&', '\n', '(', ')', '`'])
const PREFIXES = new Set(['do', 'then', 'else', 'elif', 'if', '!', 'time', '{', 'env', 'command', 'builtin', 'exec', 'nohup', 'sudo', 'nice', 'xargs', 'timeout', 'while', 'until'])
const PREFIX_VALUED: Record<string, Set<string>> = {
  sudo: new Set(['-u', '-g', '-C', '-h', '-p', '-U', '-r', '-t', '-D']),
  timeout: new Set(['-k', '-s', '--kill-after', '--signal']),
  xargs: new Set(['-n', '-I', '-P', '-L', '-s', '-d', '-E', '-a']),
  env: new Set(['-u', '-C', '-S', '--unset', '--chdir']),
  nice: new Set(['-n']),
  exec: new Set(['-a']),
}
const RUNNERS: Record<string, string[]> = { npx: [], bunx: [], pnpx: [], bun: ['x'], npm: ['exec', 'x'], pnpm: ['dlx', 'exec'], yarn: ['dlx', 'exec'] }
const MAX_CALLS = 50
const REDIRECT = /^(\d*>>?|\d*<|\d*>&\d*|&>>?)$/

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

function skipFlags(toks: string[], j: number, word: string): number {
  const valued = PREFIX_VALUED[word]
  while (j < toks.length && (toks[j] ?? '').startsWith('-') && !SEPARATORS.has(toks[j] ?? '')) j += valued?.has(toks[j] ?? '') ? 2 : 1
  return j
}

export function cdTo(cwd: string, dir: string, home: string): string {
  if (dir === '~' || dir.startsWith('~/')) return home && isAbsolute(home) ? resolvePath(home, dir.slice(2)) : ''
  if (dir === '-' || /[~$`]/.test(dir)) return ''
  if (isAbsolute(posix(dir))) return resolvePath('/', dir)
  return cwd && isAbsolute(cwd) && !/[~$`]/.test(cwd) ? resolvePath(cwd, dir) : ''
}

export function invocations(command: string, sessionCwd: string, home: string, wanted: (head: string) => boolean): Invocation[] {
  const text = heredocless(command)
  const toks = tokenize(text)
  const found: Invocation[] = []
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
    let j = i
    for (;;) {
      const tok = toks[j] ?? ''
      const word = tok.split('/').pop() ?? ''
      if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(tok)) j++
      else if (word === 'timeout') {
        j = skipFlags(toks, j + 1, word)
        if (/^\d/.test(toks[j] ?? '')) j++
      } else if (word === 'command' && /^-[A-Za-z]*[vV]/.test(toks[j + 1] ?? '')) break
      else if (PREFIXES.has(word)) j = skipFlags(toks, j + 1, word)
      else break
    }
    const head = toks[j]?.split('/').pop() ?? ''
    const next = toks[j + 1]
    if (head === 'cd') {
      cwd = next === undefined || SEPARATORS.has(next) ? cdTo(cwd, '~', home) : cdTo(cwd, next, home)
      continue
    }
    if (!head || !wanted(head)) continue
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
    found.push({ head, args, cwd })
    i = k - 1
  }
  const keyOf = (inv: Invocation) => [inv.head, ...inv.args].join('\0')
  const seen = new Set(found.map(keyOf))
  for (const body of substitutions(text)) {
    for (const inv of invocations(body, cwd, home, wanted)) {
      const key = keyOf(inv)
      if (seen.has(key) || found.length >= MAX_CALLS) continue
      seen.add(key)
      found.push(inv)
    }
  }
  return found
}

export function cliCalls(command: string, cwd: string, home: string): CliCall[] {
  const names = new Set(CLIS.flatMap(c => c.commands))
  const out: CliCall[] = []
  for (const inv of invocations(command, cwd, home, head => names.has(head) || head in RUNNERS)) {
    let head = inv.head
    let args = inv.args
    const subs = RUNNERS[head]
    if (subs && !names.has(head)) {
      let k = subs.length === 0 ? 0 : subs.includes(args[0] ?? '') ? 1 : -1
      if (k < 0) continue
      while (k < args.length && (args[k] ?? '').startsWith('-')) k++
      head = (args[k] ?? '').replace(/(.)@[^/]*$/, '$1')
      args = args.slice(k + 1)
    }
    const cli = CLIS.find(c => c.commands.includes(head) || c.packages.includes(head))
    if (cli) out.push({ cli, args, cwd: inv.cwd })
  }
  return out
}

function asksHelp(call: CliCall): boolean {
  return call.args.some(a => a === '--help' || a === '-h')
}

export function mutates(call: CliCall): boolean {
  const verb = call.args.find(a => !a.startsWith('-'))
  return !asksHelp(call) && verb !== undefined && call.cli.mutating.includes(verb)
}

export function deploys(call: CliCall): boolean {
  return !asksHelp(call) && call.args.filter(a => !a.startsWith('-')).slice(0, 2).some(a => call.cli.deploy.includes(a))
}
