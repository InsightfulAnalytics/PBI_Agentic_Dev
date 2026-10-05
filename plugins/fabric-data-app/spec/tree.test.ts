import { expect, test } from 'claude-code/testing'

import { mapLimit, replaceChildren, resolvePath, useDrives } from '../hooks/tree'

test('resolvePath: canonical absolute folders that keep POSIX and drive roots', () => {
  expect(resolvePath('/work/app', '.')).toBe('/work/app')
  expect(resolvePath('/work/app', '../other//x/./')).toBe('/work/other/x')
  expect(resolvePath('/work', '/')).toBe('/')
  expect(resolvePath('/work', '/../..')).toBe('/')
  useDrives(true)
  try {
    expect(resolvePath('C:/Users/k', 'C:\\')).toBe('C:/')
    expect(resolvePath('C:/Users/k', '..\\..\\Apps\\.')).toBe('C:/Apps')
    expect(resolvePath('C:/Users/k', '/d/work/..')).toBe('D:/')
  } finally {
    useDrives(false)
  }
})

const node = (id: string, kind: 'dir' | 'file' = 'dir', loaded = false) => ({ id, parent: id.slice(0, id.lastIndexOf('/')) || '/', name: id.split('/').pop() ?? id, kind, hidden: false, mtime: 0, loaded })

test('replaceChildren: every listed folder in one pass keeps loaded state, drops what is gone with its subtree, and marks listed folders loaded', () => {
  const nodes = [node('/w/a', 'dir', true), node('/w/a/x', 'dir', true), node('/w/a/x/deep', 'file'), node('/w/a/y', 'dir', true), node('/w/a/y/z', 'file'), node('/w/b', 'dir')]
  const out = replaceChildren(
    nodes,
    new Map([
      ['/w/a', [node('/w/a/y'), node('/w/a/new', 'file')]],
      ['/w/a/x', [node('/w/a/x/orphan', 'file')]],
      ['/w/b', [node('/w/b/c', 'file')]],
    ]),
  )
  expect(out.map(n => [n.id, n.loaded])).toEqual([
    ['/w/a', true],
    ['/w/a/y/z', false],
    ['/w/b', true],
    ['/w/a/y', true],
    ['/w/a/new', false],
    ['/w/b/c', false],
  ])
  const big = Array.from({ length: 4000 }, (_, i) => node(`/w/d${i}`, 'dir', true))
  const listed = new Map(big.map(d => [d.id, Array.from({ length: 10 }, (_, j) => node(`${d.id}/f${j}`, 'file'))]))
  expect(replaceChildren(big, listed).length).toBe(44_000)
})

test('mapLimit keeps at most the limit in flight and returns results in order', async () => {
  let live = 0
  let peak = 0
  const out = await mapLimit(Array.from({ length: 40 }, (_, i) => i), 16, async i => {
    live += 1
    peak = Math.max(peak, live)
    await Promise.resolve()
    await Promise.resolve()
    live -= 1
    return i * 2
  })
  expect(peak).toBe(16)
  expect(out).toEqual(Array.from({ length: 40 }, (_, i) => i * 2))
})
