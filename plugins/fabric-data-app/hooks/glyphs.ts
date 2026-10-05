export type Tier = 'fabric' | 'nerd' | 'plain'
type Rgb = [number, number, number]
type Glyph = { fabric: number; nerd: string; plain: string; rgb: Rgb }

const GLYPHS: Record<string, Glyph> = {
  app: { fabric: 991302, nerd: '\u{f003b}', plain: '▣', rgb: [29, 83, 164] },
  SemanticModel: { fabric: 991234, nerd: '\u{f01bc}', plain: '◆', rgb: [90, 64, 156] },
  Lakehouse: { fabric: 991258, nerd: '\u{f0b9d}', plain: '◇', rgb: [29, 83, 164] },
  Warehouse: { fabric: 991243, nerd: '\u{f0a0b}', plain: '▤', rgb: [29, 83, 164] },
  SQLDatabase: { fabric: 991280, nerd: '\u{f1063}', plain: '▦', rgb: [0, 142, 230] },
  KQLDatabase: { fabric: 991255, nerd: '\u{f1063}', plain: '▦', rgb: [0, 142, 230] },
  UserDataFunction: { fabric: 991284, nerd: '\u{f0295}', plain: 'ƒ', rgb: [63, 125, 53] },
  function: { fabric: 0, nerd: '\u{f0295}', plain: 'ƒ', rgb: [63, 125, 53] },
}

const TABLE: Glyph = { fabric: 0, nerd: '\u{f04eb}', plain: '⊞', rgb: [0, 142, 230] }

function hls(rgb: Rgb): [number, number, number] {
  const [r, g, b] = rgb.map(v => v / 255) as Rgb
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  const range = max - min
  if (range < 1e-6) return [0, l, 0]
  const s = l <= 0.5 ? range / (max + min) : range / (2 - max - min)
  const rc = (max - r) / range
  const gc = (max - g) / range
  const bc = (max - b) / range
  const h = r === max ? bc - gc : g === max ? 2 + rc - bc : 4 + gc - rc
  return [(((h / 6) % 1) + 1) % 1, l, s]
}

function component(m1: number, m2: number, hue: number): number {
  const h = ((hue % 1) + 1) % 1
  if (h < 1 / 6) return m1 + (m2 - m1) * h * 6
  if (h < 0.5) return m2
  if (h < 2 / 3) return m1 + (m2 - m1) * (2 / 3 - h) * 6
  return m1
}

function lifted(rgb: Rgb): string {
  const [h, l0, s] = hls(rgb)
  const l = Math.max(l0, 0.62)
  const out =
    s < 1e-6
      ? [l, l, l]
      : (() => {
          const m2 = l <= 0.5 ? l * (1 + s) : l + s - l * s
          const m1 = 2 * l - m2
          return [h + 1 / 3, h, h - 1 / 3].map(x => component(m1, m2, x))
        })()
  return '#' + out.map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('')
}

export function glyphFor(kind: string, tier: Tier): { char: string; color: string } {
  const g = GLYPHS[kind] ?? TABLE
  const char = tier === 'fabric' && g.fabric ? String.fromCodePoint(g.fabric) : tier === 'plain' ? g.plain : g.nerd
  return { char, color: lifted(g.rgb) }
}

export const KIND_LABEL: Record<string, string> = {
  SemanticModel: 'semantic model',
  Lakehouse: 'lakehouse',
  Warehouse: 'warehouse',
  SQLDatabase: 'SQL database',
  KQLDatabase: 'KQL database',
  UserDataFunction: 'user data functions',
}

export const CONNECTOR_KIND: Record<string, string> = {
  'fabric-semanticmodel': 'SemanticModel',
  'fabric-lakehouse': 'Lakehouse',
  'fabric-warehouse': 'Warehouse',
  'fabric-sqldatabase': 'SQLDatabase',
  'fabric-sql': 'SQLDatabase',
  'fabric-kqldatabase': 'KQLDatabase',
  'fabric-kusto': 'KQLDatabase',
  kusto: 'KQLDatabase',
}
