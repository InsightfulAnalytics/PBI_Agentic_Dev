---
name: rayfin-fabric-cli
version: 26.40.3
description: Operational gotchas for building Microsoft Fabric Apps with the Rayfin scaffold and the `fabric-app-data` / `rayfin` CLIs (Vite + React data apps over a published semantic model, with optional Fabric SQL DB writeback via DAB GraphQL). Invoke on TLS/certificate errors from npm/npx or the Fabric SDK, "rayfin up" / "db apply" failures, `fabric-app-data query` "too many arguments", "Dialect is required when Data module is enabled", "No compiled data/*.js files found", TS6377 tsBuildInfo errors, a writeback `create()` that silently never lands a row, UUID primary-key / `NEWID()` issues, or enabling the data service on an app scaffolded without it. Also invoke before scaffolding a new app (`npm create @microsoft/rayfin`, `rayfin init`), before passing `--overwrite`, when a fresh `dataapp` scaffold has no `fabric-visuals` or `src/queries`, when the scaffold's install fails with EALLOWSCRIPTS, or when running DAX through `fabric-app-semantic-model-tools run-dax-query`. Covers scaffold target safety, the template versions (SDK or connector), NODE_OPTIONS, the npm 11.16 allow-scripts failure, AVG HTTPS-shield interference, query CLI syntax, what the first `rayfin up` changes, the five edits to turn on writeback, and client-supplied UUID ids.
---

# Rayfin / Fabric-App CLI gotchas

Traps specific to the Rayfin data-app scaffold (`npm create @microsoft/rayfin`), the
`fabric-app-data` SDK, and Fabric SQL DB writeback. Read before fighting TLS errors or a
"won't deploy / won't post" writeback bug.

## Scaffold only into a new, empty folder: `--overwrite` deletes the target

`npm create @microsoft/rayfin@latest -- "<name>" --template dataapp` creates `<name>/`. Never
point it at a folder that already holds work, and never pass `--overwrite`. On a non-empty
target, consenting to overwrite (the prompt or the flag) runs `wipeTargetDirectory`, an
`rmSync(target, { recursive: true, force: true })`, before anything is written: the folder and
everything in it are gone, not merged. A project folder with a workbook, PBIP or notes beside the
app gets the app in a subfolder. (Read from rayfin-cli 1.36.2,
`dist/utils/scaffold-pipeline.js`, 19 Oct 2026.)

## Use `@latest`: an old cached `dataapp` template is a different starter

The npx cache can hold an old rayfin-cli. Its 1.33.1 `dataapp` template is a writeback starter
(`rayfin-client`, `react-router-dom`) with no `fabric-visuals`, `src/queries`, `AGENTS.md` or
`.agents/skills`. From 1.36 the same template name is the Fabric Apps Analytics template. If a
fresh scaffold has no `@microsoft/fabric-visuals` in `package.json` and no `src/queries`, rerun
with `@latest`. Its agent skills are also newer than copies in older apps, so take them from a
fresh scaffold rather than copying them across.

The 1.36 template itself moved on in late October 2026, so two apps on "1.36" can differ:

| | Mid-October 1.36 | Late-October 1.36 (Reading Room, 31 Oct 2026) |
| --- | --- | --- |
| Model link | `fabric.yaml`, the `fabric-app-data` SDK | a connector in `rayfin/rayfin.yml` (`type: fabric-semanticmodel`, a `name` used as the connection) |
| Query hook | `use-semantic-model-query` over the SDK | `useSemanticModelQuery({ connection, query })` over `@microsoft/rayfin-connector-fabric-semanticmodel` |
| CLI DAX | `npx fabric-app-data query semanticModel <alias> -f <file>` | `npx fabric-app-semantic-model-tools run-dax-query --dax <file> --alias <connection>` |
| Charts | `fabric-visuals` | `fabric-visuals`, `fabric-datagrid` and `fabric-visuals-extensibility` 5.0.0 |

Neither one is the stale starter: check which you have before following an older app's code.

## Every npm/npx call needs `NODE_OPTIONS='--use-system-ca'`

```powershell
$env:NODE_OPTIONS='--use-system-ca'
```

Without it the Fabric SDK's HTTPS requests fail cert validation against
corporate-CA-signed endpoints. Set it once per shell.

## npm 11.16 stops the scaffold's install: EALLOWSCRIPTS

The scaffold copies the template, then runs an install with `--allow-scripts`, which npm 11.16
refuses in a project-scoped install ("--allow-scripts is not allowed in project-scoped installs.
Add the entries to the "allowScripts" field in package.json, or to .npmrc, instead."). The files
are all there; run `npm install` in the new folder. npm then skips the install scripts of seven
packages (esbuild, @swc/core, keytar, msal-node-runtime and others) with a warning, and `vite`,
`vitest`, `rayfin login` and `rayfin up` still work (31 Oct 2026).

## The first `rayfin up` edits `rayfin/rayfin.yml`

It adds the deployed app's URL to `services.auth.allowedRedirectUris` and sets
`staticHosting.assetAccess: protected`. Commit both with the app.

## AVG Web/Mail Shield breaks `query`, `add --from-url`, and `rayfin up`

If you still get TLS errors *after* the NODE_OPTIONS above, AVG is MITM-ing the HTTPS
connection. Disable Web/Mail Shield (or whitelist the Fabric endpoints) before running
those three commands.

## `fabric-app-data query` syntax: `<sourceType> <alias>`, text in `-q`/`-f`

```powershell
# ❌ "too many arguments for 'query'"
npx fabric-app-data query starwars --query "EVALUATE ..."

# ✅
npx fabric-app-data query semanticModel starwars -q "EVALUATE ..."
npx fabric-app-data query semanticModel starwars -f path/to/query.dax
```

On the connector template, `run-dax-query` takes one to four `--dax` files per call ("Provide
one to four --dax files"), so check a folder of queries in batches of four:

```bash
NODE_OPTIONS=--use-system-ca npx fabric-app-semantic-model-tools run-dax-query \
  --dax src/queries/a.dax --dax src/queries/b.dax --alias reading
```

## Enabling writeback on an app scaffolded WITHOUT the data service: five edits

`data: { enabled: false }` at scaffold time means the whole data-service scaffold is
missing. Turning on writeback (Fabric SQL DB via DAB GraphQL) needs **all five**; miss one
and `rayfin up` / `db apply` fails cryptically:

1. **`rayfin.yml` needs a dialect.** `data: { enabled: true }` alone →
   `400 … Dialect is required when Data module is enabled`. Add `dialect: mssql`
   (Fabric SQL DB is T-SQL).
2. **`rayfin/tsconfig.json` must exist.** Without it, `db apply` says "TypeScript
   compilation successful" then `❌ No rayfin/.temp/compiled/data/*.js files found`. Copy
   the template's: `extends ../tsconfig.json`, `outDir .temp/compiled`, `composite: true`,
   `noEmit: false`, `module`/`moduleResolution: nodenext`.
3. **Root `tsconfig.json` must reference it:** `"references": [{ "path": "./rayfin" }]`.
4. **Distinct `tsBuildInfoFile`.** If `rayfin` extends a root tsconfig that sets
   `tsBuildInfoFile`, it inherits the same path → `tsc -b` fails **TS6377**
   ("will overwrite .tsbuildinfo generated by referenced project"). Override it in
   `rayfin/tsconfig.json` (e.g. `".temp/rayfin.tsbuildinfo"`).
5. **`rayfin/data/schema.ts` needs a runtime array, not just a type.** The CLI discovers
   entities from `export const schema = [BudgetAdjustment]` (a *value* import of the class).
   A type-only `export type AppSchema = {...}` compiles but registers nothing.

**Deploy order:** `npx rayfin up` provisions the SQL DB child item, applies settings/static,
and runs the schema apply itself. If that step fails, fix the above and re-run
`npx rayfin up db apply`. The standalone `db apply` is **remote-only** and needs the compiled
artifacts to already exist.

## UUID primary keys have NO `DEFAULT NEWID()`: supply `id` client-side

The docs claim the server generates a UUID if you omit `id`. **Not true here.** Rayfin's DDL
only emits a column default when the decorator sets one (`@uuid({ default: … })`); a plain
`@uuid() id` produces `UNIQUEIDENTIFIER NOT NULL` with no default, so a `create()` that omits
`id` fails the PK constraint. The DAB client catches nothing, so a `try/catch` swallows it and
the row silently never lands (table stays empty, the draft "won't post"). Fix:

```ts
await api.BudgetAdjustment.create({ id: crypto.randomUUID(), year, /* … */ });
```

**Corollary: never let a writeback `catch` be silent.** Surface the error in the UI and
`console.error` it; a "nothing happens on click" write bug is otherwise invisible. Check the
PK/`id` *first*; auth is usually fine: `postedAt` as an ISO-8601 string (trailing `Z`) is
accepted by `DATETIME2`, and `@authenticated('*')` writes carry the user token automatically
via the shared `RayfinClient` singleton.
