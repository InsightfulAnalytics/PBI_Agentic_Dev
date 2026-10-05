import { expect, test } from 'claude-code/testing'

import { parseSources } from '../hooks/apps'
import { fromRayfin } from '../hooks/rayfin'

const WS = '11111111-1111-1111-1111-111111111111'
const ITEM = '22222222-2222-2222-2222-222222222222'
const none = { fabricYaml: '', rayfinYml: '', schemaTs: '', udfDefs: [], tsFunctions: [] }

test('rayfin.yml: the app name is the top-level key and connectors parse whatever their key order', () => {
  const yml = `connectors:\n  - type: fabric-lakehouse\n    name: gold # curated\n    config:\n      itemId: "${ITEM}"\n  - name: 'sales model'\n    type: fabric-semanticmodel\nname: my-app\n`
  expect(fromRayfin('/work/app', yml, '').name).toBe('my-app')
  expect(parseSources({ ...none, rayfinYml: yml })).toEqual([
    { kind: 'Lakehouse', name: 'gold', note: 'lakehouse', item: ITEM },
    { kind: 'SemanticModel', name: 'sales model', note: 'semantic model', item: undefined },
  ])
  expect(parseSources({ ...none, rayfinYml: 'connectors:\n- name: flat\n  type: fabric-warehouse\n' })).toEqual([{ kind: 'Warehouse', name: 'flat', note: 'warehouse', item: undefined }])
  expect(fromRayfin('/work/app', 'services:\n  data:\n    name: inner\n', '').name).toBe('app')
})

test('.deployments.json: wrong field types and bad JSON become an error on the app, never a throw', () => {
  const typed = fromRayfin('/work/app', 'name: a\n', JSON.stringify({ deployments: { x: { fabricItemId: ITEM, fabricWorkspaceId: WS, fabricDeepLink: 123 } } }))
  expect(typed.item).toBe(ITEM)
  expect(typed.portal).toBe(`https://app.fabric.microsoft.com/groups/${WS}/appbackends/${ITEM}`)
  expect(typed.error).toContain('x.fabricDeepLink')
  expect(fromRayfin('/work/app', 'name: a\n', '{"deployments":').error).toContain('not valid JSON')
  expect(fromRayfin('/work/app', 'name: a\n', '').error).toBe('')
})
