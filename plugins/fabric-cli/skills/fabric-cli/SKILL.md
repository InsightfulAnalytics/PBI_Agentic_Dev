---
name: fabric-cli
version: 26.26
description: Expert guidance for using the Fabric CLI (`fab`) to fully interact with Fabric workspaces, items, and configuration. Automatically invoke this skill whenever the user mentions "Fabric" or "Power BI Service" or a "Fabric/Power BI workspace".
---

# Fabric CLI

Guidance for using `fab` to programmatically manage Fabric & Power BI service

- Install via `uv tool install ms-fabric-cli` (get `uv` via `winget install uv` or `brew install uv`)
- Fabric CLI is for working with the Cloud environment and not local files; it works with Power BI Pro, PPU, or Fabric; you DO NOT need a Fabric SKU to use the Fabric CLI
- Keep `fab` current: check the installed version against the latest `ms-fabric-cli` release and upgrade with `uv tool upgrade ms-fabric-cli` unless the user has pinned a specific version. Discover commands and flags with `fab --help` and `fab <command> --help` rather than hard-coding behavior; the CLI surface changes regularly

> [!IMPORTANT]
> When you learn something generic about `fab` (an error and its real cause, a request shape the
> docs get wrong, an undocumented response envelope, a prerequisite that is not written down),
> record it where it will still be true for the next reader. Service and API behaviour goes in the
> `references/*.md` file that already owns that topic; the reference map at the end of this file is
> the index. Anything that names an operating system, a shell, an installed binary or a `fab`
> version carries its scope in the sentence, per the boundary rule below.
>
> This skill folder is the only copy that ships. A note in a per-agent memory file is per-machine
> and per-user, so a second machine, a Codespace, and everyone else running this plugin never see it.
>
> Generic learnings only, never item- or task-specific ones. Do not write a change log. If the fact
> is already in the skill, improve the one copy rather than restating it somewhere else.

<!-- boundary-rule:begin -->
## Where a new learning goes

Three questions, in order. Stop at the first yes.

**1. Is it true only because of how THIS machine is set up right now?**
An installed path, which identity you are logged in as, a preview toggle, a console codepage, which
build happens to be installed. Then it is machine-local.

Before accepting that answer, try to generalise it. Most machine-local facts are the residue of a
search that succeeded once, and the search is the portable part:

| Instead of recording | Record |
| --- | --- |
| the path where you found a DLL | the probe that finds it, and how to tell which host can load it |
| that a preview toggle is off here | the verbatim symptom string, and the route that works regardless |
| which account has rights here | the check that reveals the mismatch |
| that a script cannot find a binary | a fix to the script |

If the generalised form survives, it is not machine-local: take it to question 2 or 3. If nothing
survives, because the fact is about one machine, one tenant or one person, write it to the agent's
own memory file and nowhere else. It would mislead an agent anywhere else, and this repository is
public.

**A Codespace has no legitimate machine-local layer.** A fact about a Codespace is true of every
Codespace built from the same devcontainer, which makes it a fact about that image. Commit it.
Never start a memory file inside a container.

**2. Is it true only where Power BI Desktop runs, only in a Windows shell, or only at some tool
version?**
Then it is portable knowledge with a boundary. It goes in this skill's `references/`, with the
boundary in the sentence:

- Platform: open or close with the scope. "On a cp1252 Windows console ... Linux and macOS never
  hit this." "Power BI Desktop only."
- Version: write the symptom and the check as the instruction, never the version. "If `fab find`
  errors, run `fab --version` before assuming a syntax problem." Put the version and date you
  observed in brackets at the end, never in the imperative. A version in the imperative rots into a
  lie; a version in brackets rots into a footnote.
- A dated or version-pinned claim also carries a `Retest:` line naming the one command that settles
  it, plus a `Verified <date>` stamp. `scripts/check-skill-hygiene.py` reports the stale ones and
  fails on a version claim with no `Retest:`.

**A scoped statement that is a ROUTE is not finished until it names the substitute in the same
sentence.** "`pbir desktop screenshot` is Windows and Desktop only" leaves a Linux agent stuck.
"`pbir desktop screenshot` is Windows and Desktop only; where Desktop is unavailable, render
server-side with the `ExportTo` API (fabric-cli `references/reports.md`)" does not.

**3. Otherwise it is a fact about the file format, the product, or the service API.**
True everywhere, including a Codespace with no Desktop and no Windows. It goes in this skill's
`references/` with no qualifier, or in `SKILL.md` when the agent must know it before opening any
reference. This is the default and where most learnings land.

### Two tests that settle almost every case

- *Would this sentence still be true in a Linux Codespace with no Power BI Desktop?* Yes means
  question 3. No, but only because Desktop is missing, means question 2. No, because the sentence
  names a path, a version or a toggle, means question 1, so run the generalisation table first.
- *Could anyone else running this plugin act on it?* If not, question 1.

### When torn, file it in the more public place

An over-cautious scope clause on a portable fact costs a reader one clause. A machine-local fact
shipped as product knowledge misleads everyone who installs the plugin.

### Where to write it

If `PBI_MARKETPLACE_ROOT` is set, a writable clone of this marketplace is on the machine:
`bash "$PBI_MARKETPLACE_ROOT/scripts/record-learning.sh"` writes the note, runs the hygiene scan,
commits to a branch and opens a pull request.

If it is unset, the skills are loading from a read-only plugin cache and an edit there is discarded
by the next `plugin update`. Write the note to the agent's memory file instead, and say plainly in
the note that it still needs promoting into the plugin.

Nothing portable belongs in `~/.claude/rules/`, `.cursor/rules/` or `.github/instructions/`. Those
are per-machine and per-user.
<!-- boundary-rule:end -->

## When to use this skill

- Use whenever the user mentions "Fabric" or "Power BI"
- Use when user asks about Power BI workspaces, deployment, tenants, publishing, download, permissions, or data


## Critical general rules

- IMPORTANT: The first time you use `fab` run check that it is up to date to the latest version (upgrade with `uv tool upgrade ms-fabric-cli` unless the user has pinned a version) and run `fab auth status`; If user isn't authenticated, ask them to run `fab auth login`
- On a Windows console left on the cp1252 codepage, `fab` dies part-way through its own output with `'charmap' codec can't encode character` even though the server-side work succeeded; export `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` in every shell block that calls `fab` (details in [reference.md](./references/reference.md#console-encoding-on-windows)). Linux and macOS never hit this
- Always use `fab --help` and `fab <command> --help` the first time you use a command to understand its syntax
- You must search the skill /references/ for relevant reference files that explain certain commands, examples, scripts, or workflows before you start using `fab`
- Before first use, ask the user if they have Fabric admin access, sensitivity labels or DLP policies, any API restrictions, or preferences for Fabric/Power BI API usage; remind user to add this to memory files
- If workspace or item name is unclear, ask the user first, then verify with `fab ls` or `fab exists` before proceeding
- Ensure that you avoid removing or moving items, workspaces, or definitions, or changing properties without explicit user direction
- If a command is blocked in your permissions and you try to use it, stop and ask the user for clarification; never try to circumvent it
- Create output directories before export: `fab export` does not create intermediate directories; `mkdir -p` the output path first or the command fails with `[InvalidPath]`


### Use `-f` (force) for non-interactive use

The `fab` CLI prompts for confirmation, so you **you must always append `-f`** to prevent this UNLESS sensitivity labels are enabled, in which case you must ask the user. Do this for the commands:

- `fab get -q "definition"` ; sensitivity label confirmation
- `fab export` ; sensitivity label confirmation
- `fab import` ; overwrite confirmation
- `fab cp` / `fab cp -r` ; overwrite and sensitivity label confirmation
- `fab rm` ; delete confirmation
- `fab assign` / `fab unassign` ; capacity/domain assignment confirmation
- `fab mv` ; rename/move confirmation


## Quickstart guide

You must read and understand the common list of operations with simple examples

0. Check the commands, syntax, and auth status: `fab --help` and `fab auth status`
1. Check if the item exists if the user gave the workspace and item name: `fab exists "spaceparts-dev.Workspace/spaceparts-otc-full.SemanticModel"`
2. Find an item by name across every workspace the user can see: `fab find 'sales' -P type=Report -l` (substring on name, description, workspace; `-P type=` to filter, `-l` for ids; `-q '<jmespath>'` for client-side filter/projection). For governance workflows that need last visit / last refresh / owner / storage mode / capacity SKU, use [`scripts/search_across_workspaces.py`](./scripts/search_across_workspaces.py); see [workspaces.md](./references/workspaces.md#cross-workspace-search) for the delta.
3. Find the workspace: `fab ls`
4. Find the item: `fab ls "Workspace Name.Workspace"`
4. Check the commands for that item: 
   - `fab desc` to get itemTypes
   - `fab desc .<ItemType>` for commands i.e. `fab desc .SemanticModel`
5. What's in that item; what's it for; what is it?:
   - Full TMDL definition: `fab get "spaceparts-dev.Workspace/spaceparts-otc-full.SemanticModel" -q "definition" -f`
   - Search a specific measure / table / column: `fab get "ws.Workspace/Model.SemanticModel" -q "definition" -f | rga -i "Sales Amount"`
   - Retrieve AI instructions / AI schema: `python3 scripts/get_semantic_model_ai_metadata.py "ws.Workspace/Model.SemanticModel" --instructions-out instructions.md --schema-out schema.json`
6. Get files, tables, or table schemas:
   - List lakehouse files: `fab ls "ws.Workspace/LH.Lakehouse/Files"`
   - List lakehouse tables: `fab ls "ws.Workspace/LH.Lakehouse/Tables"`
   - Table schema: `fab table schema "ws.Workspace/LH.Lakehouse/Tables/gold/orders"`
7. Query data (always prefer the wrapper scripts over raw `fab api` / `duckdb` / `sqlcmd`; they resolve IDs, hosts, and auth for you):
   - Semantic model (DAX): `python3 scripts/execute_dax.py "ws.Workspace/Model.SemanticModel" -q "EVALUATE TOPN(10, 'Orders')"`
   - Lakehouse SQL endpoint, warehouse, or SQL database (T-SQL): prefer the `fabric-sql` MCP `execute_query(workspaceId, itemId, query)` when it is loaded; fall back to `python3 scripts/query_sql_endpoint.py "ws.Workspace/LH.Lakehouse" -q "SELECT TOP 10 * FROM dbo.orders"`. See [querying-data.md](./references/querying-data.md#querying-the-sql-endpoint-route-priority)
   - Lakehouse or warehouse Delta over OneLake (DuckDB): `python3 scripts/query_lakehouse_duckdb.py "ws.Workspace/LH.Lakehouse" -q "SELECT * FROM tbl LIMIT 10" -t gold.orders`
8. Set properties for an item or workspace: `fab set "ws.Workspace/Item.Notebook" -q displayName -i "New Name"` or `fab set "ws.Workspace" -q description -i "Production environment"`
9. Review or manage permissions:
   - Item ACL: `fab acl ls "ws.Workspace/Model.SemanticModel"` then `fab acl set "ws.Workspace/Model.SemanticModel" -I user@contoso.com -R Read`
   - Workspace roles: `fab acl ls "ws.Workspace"` then `fab acl set "ws.Workspace" -I user@contoso.com -R Member`
   - Setting up a service principal for automation instead of a human identity: [service-principals.md](./references/service-principals.md) - creation via az CLI, the workspace-role-plus-tenant-setting-group double requirement, and how to authenticate `fab` as it
10. Deploy items to Fabric: `fab import "ws.Workspace/New.Notebook" -i ./local-path/Nb.Notebook -f`
11. Download items from Fabric: `fab export "ws.Workspace/Nb.Notebook" -o ./backup -f` (always `mkdir -p ./backup` first)
12. Copy or move items between workspaces: `fab cp "dev.Workspace/Item.Notebook" "prod.Workspace" -f` or `fab mv "ws.Workspace/Old.Notebook" "ws.Workspace/New.Notebook" -f`
13. Open item in Fabric via browser: `fab open "spaceparts-dev.SpaceParts/Amazing Report.Report"`
14. Using Fabric or Power BI APIs: `fab api -A powerbi "groups/<ws-id>/datasets/<model-id>/refreshes" -X post -i '{"type":"Full"}'` or `fab api "workspaces/<ws-id>/items"`
15. Using [Azure CLI](./references/fab-vs-az-cli.md) (advanced) when Fabric CLI doesn't suffice:
    - T-SQL over any SQL-capable item ; use [`scripts/query_sql_endpoint.py`](./scripts/query_sql_endpoint.py) (reuses `az login` via `ActiveDirectoryAzCli`; full walkthrough in [querying-data.md](./references/querying-data.md#sqlcmd-over-lakehouse-warehouse-and-sql-database))
    - Pass a Key Vault secret to a consumer without ever reading, echoing, or persisting it: `az login --service-principal -u <appId> -t <tenantId> --password "$(az keyvault secret show --vault-name <vault> --name <secret> --query value -o tsv)"` ; command substitution pipes the secret directly into the child process arg list, never stdout, a file, or a named shell variable
    - Calling `az` from a Python script on Windows needs two accommodations that Linux and macOS do not: resolve the executable with `shutil.which("az")` so `PATHEXT` is honoured, and pass the command as one string with `shell=True` under Git Bash ; [fab-vs-az-cli.md](./references/fab-vs-az-cli.md#calling-az-from-a-script)
    - Full fab-vs-az decision matrix: [fab-vs-az-cli.md](./references/fab-vs-az-cli.md)


## Essential Concepts

For information about any concepts related to Power BI or Fabric you must search or fetch via the `microsoft-learn` MCP server (or the `pbi-search` CLI as an alternative) and ask the user questions with the `AskUserQuestion` tool; NEVER guess or make assumptions.

### Workspaces

- **Workspaces** are containers for **items** like Notebooks (and other ETL items), Lakehouses (and other data items), SemanticModels, Reports (and other consumption items), and OrgApps.
- Workspaces can be assigned to different things:
  - Deployment Pipelines for lifecycle management (Dev, Test, Prod, etc.)
  - Domains for governance and tenant structuring
  - Capacities for licensing and resources (Fabric or Premium capacities only; PPU and Pro work differently)
  - Git repositories for Source Control via Git integration


## Key Patterns

Pay special attention to each of the following areas when using the Fabric CLI


### Path Format

Fabric uses filesystem-like paths with type extensions:

`"WorkspaceName.Workspace/ItemName.ItemType"`

You must quote paths with spaces and punctuation:

`"Workspace Name.Workspace/Semantic Model Name.SemanticModel"`

For lakehouses this is extended into files and tables:

`WorkspaceName.Workspace/LakehouseName.Lakehouse/Files/FileName.extension` or `/WorkspaceName.Workspace/LakehouseName.Lakehouse/Tables/TableName`

For Fabric capacities you have to use `fab ls .capacities`

Examples:

- `"Production Workspace.Workspace/Sales Report.Report"`
- `Data.Workspace/MainLH.Lakehouse/Files/data.csv`
- `Data.Workspace/MainLH.Lakehouse/Tables/dbo/customers`


### Common Item Types

- `.Workspace` - Workspaces
- `.SemanticModel` - Power BI datasets
- `.Report` - Power BI reports
- `.Notebook` - Fabric notebooks
- `.DataPipeline` - Data pipelines
- `.Lakehouse` / `.Warehouse`/ `.SQLDatabase` - Data artifacts
- `.SparkJobDefinition` - Spark jobs
- `.AISkill` - Fabric Data Agents
- `.MirroredDatabase` / `.MirroredWarehouse` - Mirrored databases
- `.Environment` - Spark environments
- `.UserDataFunction` - User data functions

Full list: You must use `fab desc` or `fab desc .<ItemType>` to check syntax and types if the user asks about an item type not listed above.


### JMESPath Queries

Filter and transform JSON responses with `-q`:

```bash
# Get single field
-q "id"
-q "displayName"

# Get nested field
-q "properties.sqlEndpointProperties"
-q "definition.parts[0]"

# Filter arrays
-q "value[?type=='Lakehouse']"
-q "value[?contains(name, 'prod')]"

# Get first element
-q "value[0]"
-q "definition.parts[?path=='model.tmdl'] | [0]"
```

### Using `fab api`

`fab` has an api escape hatch that lets you use any API even if it doesn't have primary commands.


#### Variable Extraction Pattern

To use `fab api` you need item IDs. Extract them like this:

```bash
WS_ID=$(fab get "ws.Workspace" -q "id" | tr -d '"')
MODEL_ID=$(fab get "ws.Workspace/Model.SemanticModel" -q "id" | tr -d '"')

# Then use in API calls
fab api -A powerbi "groups/$WS_ID/datasets/$MODEL_ID/refreshes" -X post -i '{"type":"Full"}'
```


#### Admin APIs (Requires Admin Role)

Don't use admin commands or APIs if the user doesn't have Admin access. Here's some examples:

```bash
# Find semantic models by name (cross-workspace)
fab api "admin/items" -P "type=SemanticModel" -q "itemEntities[?contains(name, 'Sales')]"

# Find all notebooks
fab api "admin/items" -P "type=Notebook" -q "itemEntities[].{name:name,workspace:workspaceId}"

# Find all lakehouses
fab api "admin/items" -P "type=Lakehouse"

# Common types: SemanticModel, Report, Notebook, Lakehouse, Warehouse, DataPipeline, Ontology
```

For full admin API reference (cross-workspace discovery, tenant settings read/update, capacity/domain/workspace overrides, activity events): [admin.md](./references/admin.md)


### Error Handling & Debugging

```bash
# Show response headers
fab api workspaces --show_headers

# Verbose output
fab get "Production.Workspace/Item" -v

# Save responses for debugging (fab api has no -o flag; redirect stdout)
fab api workspaces > /tmp/workspaces.json
```


## Common workflows

These are the most common workflows you'll encounter in Fabric

### Finding or exploring workspaces, items, or metadata

| Command | Purpose | Example |
|---|---|---|
| `fab ls` | List workspaces / items | `fab ls "Sales.Workspace" -l` |
| `fab exists` | Check if a path exists | `fab exists "Sales.Workspace/Model.SemanticModel"` |
| `fab get` | Get item details | `fab get "Sales.Workspace" -q "id"` |
| `fab desc` | Supported commands per type | `fab desc .SemanticModel` |

Flags:
- `-l` (long listing)
- `-a` (show hidden items)
- `-q` (JMESPath filter)
- `-v` (verbose output)
- `-o` (save response to file)

Fabric discovery follows a drill-down pattern:

- Browsing:
  - List workspaces: `fab ls`
  - List items in a workspace: `fab ls "ws.Workspace" -l`
  - Confirm a path exists: `fab exists "ws.Workspace/Item"`
  - Check what commands an item type supports: `fab desc .<ItemType>`
- Inspection:
  - Get item details: `fab get "ws.Workspace/Item"`
  - Pull a single field: `fab get "ws.Workspace" -q "id"`
- Cross-workspace search:
  - Routine search across name, description, workspace: `fab find '<text>' -P type=<Type> -l`
  - Governance fields not in `fab find` (last visit, last refresh, owner, storage mode, capacity SKU, Copilot readiness): [`scripts/search_across_workspaces.py`](./scripts/search_across_workspaces.py); see [workspaces.md](./references/workspaces.md#cross-workspace-search) for the delta
  - Downstream reports for a given model: [`scripts/get-downstream-reports.py`](./scripts/get-downstream-reports.py)
  - Tenant-wide admin APIs: [admin.md](./references/admin.md)

Check references before exploring:

- [workspaces.md](./references/workspaces.md)
- [folders.md](./references/folders.md)
- [admin.md](./references/admin.md)
- [reference.md](./references/reference.md)


### Querying data

| Command | Purpose | Example |
|---|---|---|
| `fab get -q "definition"` | Get model schema | `fab get "ws.Workspace/Model.SemanticModel" -q "definition" -f` |
| `fab api -A powerbi` | Execute DAX | `fab api -A powerbi "groups/<ws-id>/datasets/<model-id>/executeQueries" -X post -i '{"queries":[{"query":"EVALUATE..."}]}'` |
| `fab ls` | Browse files / tables | `fab ls "ws.Workspace/LH.Lakehouse/Files"` |
| `fab table schema` | Lakehouse table schema | `fab table schema "ws.Workspace/LH.Lakehouse/Tables/sales"` |
| `fab cp` | Upload / download OneLake file | `fab cp ./local.csv "ws.Workspace/LH.Lakehouse/Files/"` |
| `duckdb` + `delta_scan` | Query Delta tables (requires DuckDB) | `duckdb -c "... delta_scan('abfss://<ws-id>@onelake.../<lh-id>/Tables/schema/table')"` |
| `duckdb` + `read_csv/json` | Query raw files (requires DuckDB) | `duckdb -c "... read_csv('abfss://.../Files/data.csv')"` |

Flags: 
- `-A fabric|powerbi|storage|azure` (API audience)
- `-X get|post|put|delete|patch` (HTTP method)
- `-i` (JSON body or file)
- `-f` (skip sensitivity prompt on definition pulls).

Fabric exposes three query paths depending on the source; always prefer the wrapper scripts -- they resolve IDs, hosts, and auth for you:

- Semantic models (DAX):
  - Find model fields first: `fab get "ws.Workspace/Model.SemanticModel" -q "definition"`
  - Query: [`scripts/execute_dax.py`](./scripts/execute_dax.py)
- Lakehouses / Warehouses via Delta over OneLake (DuckDB):
  - Query a single table: [`scripts/query_lakehouse_duckdb.py`](./scripts/query_lakehouse_duckdb.py) (use `tbl` as a placeholder and pass `-t schema.table`)
  - Multi-table joins or raw files in `Files/`: pass `--sql` with your own `delta_scan()` / `read_csv` / `read_json_auto` calls
  - Optionally scaffold a Direct Lake model instead: [`scripts/create_direct_lake_model.py`](./scripts/create_direct_lake_model.py)
- Lakehouse SQL endpoint, Warehouse, or SQL Database (T-SQL):
  - Prefer the `fabric-sql` MCP `execute_query(workspaceId, itemId, query)` when loaded; server-side, no local tooling
  - Fall back to [`scripts/query_sql_endpoint.py`](./scripts/query_sql_endpoint.py) (`sqlcmd`; auto-detects host per item type, reuses `az login` via `ActiveDirectoryAzCli`) when the MCP is unavailable
  - Prefer either over DuckDB when you need `INFORMATION_SCHEMA`, `sys.*` metadata, CTEs, or window functions
  - Full route priority: [querying-data.md](./references/querying-data.md#querying-the-sql-endpoint-route-priority)

Check references before writing queries:

- [querying-data.md](./references/querying-data.md)
- [semantic-models.md](./references/semantic-models.md)
- [lakehouses.md](./references/lakehouses.md)
- [warehouses.md](./references/warehouses.md)
- [sql-databases.md](./references/sql-databases.md)


### Changing metadata or access (descriptions, tags, endorsement, properties, bindings, permissions)

| Command | Purpose | Example |
|---|---|---|
| `fab set` | Update property | `fab set "ws.Workspace/Item" -q displayName -i "New Name"` |
| `fab mv` | Rename / move item | `fab mv "ws/Old.Notebook" "ws/New.Notebook" -f` |
| `fab acl ls` | List permissions | `fab acl ls "ws.Workspace"` |
| `fab acl set` | Grant permission | `fab acl set "ws.Workspace" -I <objectId> -R Member` |
| `fab acl rm` | Revoke permission | `fab acl rm "ws.Workspace" -I <upn>` |
| `fab label set` | Set sensitivity label | `fab label set "ws/Nb.Notebook" --name Confidential` |

Flags:
- `-q <field>` + `-i <value>` (set a single property)
- `-I` (object ID or UPN for `fab acl`)
- `-R Admin|Member|Contributor|Viewer` (role for `fab acl set`)
- `-f` (skip confirmation; ask user first if sensitivity labels are in play)

Metadata and access changes fall into a few groups:

- Properties (displayName, description, sensitivity config):
  - Native update: `fab set "<path>" -q <field> -i "<value>"`
  - Capture current state first so you can revert: `fab get -v -o /tmp/before.json`
- Endorsement, certification, and tags (no first-class `fab` commands):
  - Patch via `fab api` with item-specific endpoints
  - Tag workflow: [tags.md](./references/tags.md)
  - Endorsement patterns: [reference.md](./references/reference.md)
- Folder placement:
  - Move items between workspace subfolders: [folders.md](./references/folders.md)
- Access control and sensitivity labels:
  - Grant / revoke: `fab acl set`, `fab acl rm`
  - Set sensitivity label: `fab label set`
  - Verify the principal first: `az ad user show`
  - Never change permissions or labels without explicit user confirmation
- Bindings:
  - Rebind a thin `.Report` to a different `.SemanticModel`: [reports.md](./references/reports.md)
  - Semantic model source rebinds (e.g. swap a lakehouse): [semantic-models.md](./references/semantic-models.md)

Check references before changing metadata:

- [reference.md](./references/reference.md)
- [tags.md](./references/tags.md)
- [folders.md](./references/folders.md)
- [reports.md](./references/reports.md)
- [semantic-models.md](./references/semantic-models.md)

### Working with workspaces

| Command | Purpose | Example |
|---|---|---|
| `fab mkdir` | Create workspace / item | `fab mkdir "New.Workspace" -P capacityname=MyCapacity` |
| `fab assign` | Attach capacity / domain | `fab assign .capacities/cap.Capacity -W ws.Workspace -f` |
| `fab unassign` | Detach capacity / domain | `fab unassign .capacities/cap.Capacity -W ws.Workspace` |
| `fab start` / `fab stop` | Resume / pause capacity | `fab start .capacities/cap.Capacity` |
| `fab cp -r` | Fork workspace | `fab cp "dev.Workspace" "prod.Workspace" -r -f` |
| `fab rm` | Soft-delete (see [recovery](./references/reference.md#recovering-deleted-items)) | `fab rm "ws/Item.Type" -f` |

Flags:
- `-P key=value` (creation params for `fab mkdir`)
- `-W` (target workspace for `fab assign` / `fab unassign`)
- `-r` (recursive copy/move)
- `-bpc` (block on path collision for `fab cp`)
- `-f` (skip confirmation)

Workspace-scope operations fall into a few groups:

- Create and provision:
  - Create workspace: `fab mkdir "<Name>.Workspace" -P capacityname=<cap>`
  - Attach capacity or domain: `fab assign .capacities/<cap>.Capacity -W <ws>.Workspace`
  - Planning context, create/get/set surface, large storage format, Spark pools, OneLake defaults, Git: [workspaces.md](./references/workspaces.md)
- Copy, fork, download:
  - Duplicate a workspace in-tenant: `fab cp -r "dev.Workspace" "prod.Workspace"`
  - Dry-run the source tree first: `fab ls "dev.Workspace"`
  - Full local snapshot (items + lakehouse files): [`scripts/download_workspace.py`](./scripts/download_workspace.py)
- Permissions:
  - Inspect / grant / revoke: `fab acl ls | set | rm`
  - Tenant-wide governance audit: use the `audit-tenant-settings` skill from the `fabric-admin` plugin
- Connections and gateways (bound to, but outside, the workspace):
  - Credential types (WorkspaceIdentity, SPN, Basic), OAuth2 limits: [connections.md](./references/connections.md)
  - Datasource binding, credential rotation: [gateways.md](./references/gateways.md)
- Folders inside a workspace:
  - Layout, nesting, conventions: [folders.md](./references/folders.md)

Check references before modifying workspaces:

- [workspaces.md](./references/workspaces.md)
- [folders.md](./references/folders.md)
- [connections.md](./references/connections.md)
- [gateways.md](./references/gateways.md)


### Executing or scheduling jobs (notebooks, notebook cells, pipelines, semantic model refresh)

| Command | Purpose | Example |
|---|---|---|
| `fab job run` | Run synchronously | `fab job run "ws/ETL.Notebook" -P date:string=2025-01-01` |
| `fab job start` | Run asynchronously | `fab job start "ws/ETL.Notebook"` |
| `fab job run-list` | List executions | `fab job run-list "ws/Nb.Notebook"` |
| `fab job run-status` | Check status | `fab job run-status "ws/Nb.Notebook" --id <job-id>` |
| `fab job run-cancel` | Cancel a job | `fab job run-cancel "ws/Nb.Notebook" --id <job-id> -w` |
| `scripts/run_notebook_checked.py` | Run a notebook + verify its exit value (status `Completed` ≠ ETL succeeded) | `python3 scripts/run_notebook_checked.py "ws/ETL.Notebook"` |
| `fab api -A powerbi .../refreshes` | Trigger semantic model refresh | `fab api -A powerbi "groups/<ws-id>/datasets/<model-id>/refreshes" -X post -i '{"type":"Full"}'` |

Flags:
- `-P key:type=value` (parameters, type is `string|int|bool`)
- `--id` (job run ID)
- `-w` (wait on cancel)
- `--timeout` (overall timeout for synchronous runs; it can crash the client poller with `'<' not supported between instances of 'int' and 'str'` while the job still runs server-side, so do not resubmit, see [notebooks.md](./references/notebooks.md#running-notebooks))
- `--polling_interval` (status poll cadence)

Jobs map to different endpoints depending on item type:

- Notebooks and pipelines:
  - Run synchronously: `fab job run "ws/ETL.Notebook" -P date:string=2025-01-01`
  - Run asynchronously: `fab job start "ws/ETL.Notebook"`
  - Check status: `fab job run-status "ws/Nb.Notebook" --id <job-id>`
  - List history: `fab job run-list "ws/Nb.Notebook"`
  - Verify the REAL outcome: a job `Completed` only means the process finished -- a notebook can catch its own exception and exit a failure payload while still showing `Completed`. Read its exit value, or use [`scripts/run_notebook_checked.py`](./scripts/run_notebook_checked.py); details in [notebooks.md](./references/notebooks.md#the-notebooks-exit-value-the-only-reliable-success-signal)
  - Python / PySpark kernels, Livy sessions, cell-level CRUD: [notebooks.md](./references/notebooks.md)
- Semantic model refresh (not exposed as `fab job`):
  - Trigger: `fab api -A powerbi "groups/<ws-id>/datasets/<model-id>/refreshes" -X post -i '{"type":"Full"}'`
  - Check current run before starting a new one (409 if already running): `fab api -A powerbi "groups/<ws-id>/datasets/<model-id>/refreshes?\$top=1"`
  - Enhanced refresh, incremental policies, partition targeting: [semantic-models.md](./references/semantic-models.md)
- Dataflow refresh:
  - Gen1 and Gen2 have different endpoints: [dataflows.md](./references/dataflows.md)
- Scheduling:
  - Per-item schedules via the scheduler API: [notebooks.md](./references/notebooks.md), [reference.md](./references/reference.md)

Check references before running jobs:

- [notebooks.md](./references/notebooks.md)
- [semantic-models.md](./references/semantic-models.md)
- [dataflows.md](./references/dataflows.md)
- [reference.md](./references/reference.md)


### Fabric admin operations (auditing, management)

| Command | Purpose | Example |
|---|---|---|
| `fab api "admin/items"` | Cross-workspace item search | `fab api "admin/items" -P "type=SemanticModel" -q "itemEntities[?contains(name,'Sales')]"` |
| `fab api "admin/workspaces"` | Workspace inventory | `fab api "admin/workspaces"` |
| `fab api "admin/tenantsettings"` | Tenant settings | `fab api "admin/tenantsettings"` |
| `fab api "admin/capacities"` | Capacity inventory | `fab api "admin/capacities"` |
| `fab api -X post .../update` | Update tenant setting | `fab api -X post "admin/tenantsettings/<name>/update" -i body.json` |

Flags:
- `-P key=value` (query params, e.g. `type=SemanticModel`)
- `-q` (JMESPath filter)
- `-X post` + `-i` (write ops)
- `--show_headers` (inspect `Retry-After` on 429)

Admin-scope work is gated behind the Fabric / Power BI admin role. Confirm access first with `fab api "admin/capacities" 2>&1 | head -5`; if it errors, stop rather than retry.

Two entry points cover most admin tasks:

- Governance audits (tenant settings, delegated overrides, Entra SG scoping):
  - Use the `audit-tenant-settings` skill from the `fabric-admin` plugin. It owns the curated metadata baseline, the audit + change-detection script, delegated-override enumeration, and the Entra SG investigation workflow.
  - Invoke it whenever the question combines tenant posture with group membership, override scope, or drift against the baseline.
- Raw admin APIs (cross-workspace search, activity events, artifact access, item search):
  - Patterns in [admin.md](./references/admin.md)
  - Rate limit: 25 write requests / minute; honor `Retry-After` on 429
  - Print the exact command and wait for user confirmation before any destructive admin operation

Check references before admin work:

- [admin.md](./references/admin.md)
- [permissions.md](./references/permissions.md) for workspace / item ACL exposure audits


### Definitions and deployment (item definitions, deployment pipelines, git integration, cicd)

| Command | Purpose | Example |
|---|---|---|
| `fab get -q "definition"` | Read raw definition | `fab get "ws/Model.SemanticModel" -q "definition" -f` |
| `fab export` | Export item to local | `fab export "ws/Nb.Notebook" -o ./backup -f` |
| `fab import` | Import item from local | `fab import "ws/Nb.Notebook" -i ./backup/Nb.Notebook -f` |
| `fab cp` | Copy between workspaces | `fab cp "dev/Item" "prod.Workspace" -f` |
| `fab api "deploymentPipelines"` | Deployment pipelines API | `fab api "deploymentPipelines" -q "value[]"` |

Flags:
- `-o` (output path for `fab export`)
- `-i` (input path or JSON body for `fab import`)
- `--format` (definition format for export / import)
- `-f` (skip overwrite and sensitivity prompts)

> [!IMPORTANT]
> **The poll interval is by far the biggest performance lever for any definition change.**
> Creating or updating an item definition is a long-running operation (LRO): the API returns
> `202 Accepted` with a `Retry-After: 20` header. `fab import`, `nb create`, and `nb cell edit`
> wait roughly that long between status polls, so a notebook that the server finishes in ~1s
> takes them 25-60s. Neither `fab` nor `nb` exposes a knob to change that interval.
> For notebook definition changes, strongly prefer [`scripts/deploy_notebook.py`](./scripts/deploy_notebook.py),
> which polls the LRO every ~0.3s (tunable via `--poll-interval`) and creates in ~1-2s or updates
> in place in ~1s. Auto-detects create vs update. When you must roll your own for another item
> type, the rule is the same: poll `updateDefinition` / create at ~0.3s, not the advertised 20s.
> ```bash
> python3 scripts/deploy_notebook.py "ws.Workspace/ETL.Notebook" -i ./ETL.Notebook   # create or update in place
> ```

Every Fabric item has a serializable definition. Move definitions between environments depending on scope:

- Single item:
  - Round-trip locally: `fab export` then `fab import` (always `mkdir -p` the output directory first; `fab export` does not create intermediate directories and fails with `[InvalidPath]`)
    - For a `.SemanticModel` there is a second caveat: `fab export` omits `definition.pbism` and `fab import` requires it, so write `{"version":"4.2","settings":{}}` to the item root before importing or the import fails with `Workload_FailedToParseFile ... Required artifact is missing in 'definition.pbism'`; see [import-download-deploy.md](./references/import-download-deploy.md#export-output-structure)
  - Same-tenant shortcut, no local hop: `fab cp "dev/Item" "prod.Workspace"`
- Semantic model as PBIP (TMDL + blank report):
  - Export the model with `fab export`, create the report with `pbir new report`, then combine
    them with `pbir report merge-to-thick`; see [import-download-deploy.md](./references/import-download-deploy.md)
- Full workspace snapshot (items + lakehouse files):
  - Backups, offline analysis, cross-tenant forks: [`scripts/download_workspace.py`](./scripts/download_workspace.py)
- Promotion between Dev, Test, Prod:
  - Fabric deployment pipelines API (covers all item types)
  - Power BI pipelines API (Power BI items only, but finer-grained deploy flags like `allowPurgeData`, `allowTakeOver`)
  - When to use each, selective deploy, LRO polling: [deployment-pipelines.md](./references/deployment-pipelines.md)
- Git integration (connect workspace to repo, branch, commit, update from git):
  - Workspace git section in [workspaces.md](./references/workspaces.md)

Check references before deploying:

- [import-download-deploy.md](./references/import-download-deploy.md) ; export / import / copy / move, PBIP round-trips, migration patterns, rebinding gotchas
- [deployment-pipelines.md](./references/deployment-pipelines.md)
- [semantic-models.md](./references/semantic-models.md)
- [reports.md](./references/reports.md) ; includes the server-side `ExportTo` render for verifying a deployed report without Power BI Desktop
- [paginated-reports.md](./references/paginated-reports.md)
- [notebooks.md](./references/notebooks.md)
- [workspaces.md](./references/workspaces.md)


## Related skills

- `audit-tenant-settings` (in the `fabric-admin` plugin) ; Fabric governance workflow covering tenant settings, delegated overrides (capacity / domain / workspace), and the Entra security groups those settings reference. Read-only; holds the curated metadata baseline and the audit + change-detection script.

## Gotchas

- **IMPORTANT:** DON'T try to use `fab ls` on items that aren't data items (.Lakehouse, .Warehouse, etc); use `fab ls` to find workspaces and items, and use `fab get` to look at definitions
- ALWAYS Use the `-f` flag when using `fab get`, `fab import`, `fab export`, etc. as described above
- ONLY fallback to `fab api` when a command doesn't exist
- **`fab api` returns a `{status_code, text}` envelope, not the raw body:** `-q` filters must start with `text.` or they silently return `None`, there is no `-o` flag (redirect stdout), and binary bodies (PDF, PNG, XLSX, PBIX, `.rdl`) are corrupted, so fetch files over raw HTTP with an `az` bearer token. See [fab-api.md](./references/fab-api.md#output-shape-and-flags)
- **Definition changes feel slow but aren't:** `fab import` / `nb create` / `nb cell edit` take 25-60s to push a notebook definition only because they poll the LRO at the server's `Retry-After: 20`. The work is ~1s. Use [`scripts/deploy_notebook.py`](./scripts/deploy_notebook.py) (tight-polls at ~0.3s) for definition changes; the poll interval is the single biggest lever

## References

**Reference map** (which references cluster together; follow the links between them, not just this list):

```
etl / notebooks
  notebooks.md ── run jobs, exit value, scheduling
    ├─ querying-data.md ── nb exec / Livy, DuckDB/sqlcmd, SQL-endpoint sync
    └─ lakehouses.md ── attach, table ops, OneLake shortcuts, SQL-endpoint id
  (cross-plugin) executing-spark, using-duckdb  ── etl plugin: ephemeral Spark, local Delta

data items
  lakehouses.md · warehouses.md · sql-databases.md · semantic-models.md
    └─ all feed querying-data.md (route priority) and notebooks.md (load then read)

governance / deploy
  admin.md · permissions.md · tags.md · folders.md
  import-download-deploy.md ─ deployment-pipelines.md ─ workspaces.md (git status)
  (cross-plugin) audit-tenant-settings ── fabric-admin plugin
```

**Skill references:**

- [Import, Download, and Deploy](./references/import-download-deploy.md) - Export / import / copy / move items, PBIP round-trips, dev-to-prod migration patterns
- [Querying Data](./references/querying-data.md) - Query semantic models in DAX and lakehouses or warehouses in SQL with DuckDB
- [Lakehouses](./references/lakehouses.md) - Endpoints, file/table operations, OneLake paths
- [Warehouses](./references/warehouses.md) - Create, browse, query via DuckDB, load data
- [SQL Databases](./references/sql-databases.md) - Create, browse, query via DuckDB, auto-mirroring
- [Semantic Models](./references/semantic-models.md) - TMDL, DAX, refresh, storage mode
- [Reports](./references/reports.md) - Export, import, visuals, fields, and the server-side `ExportTo` render that substitutes for a Power BI Desktop screenshot where Desktop is unavailable
- [Paginated Reports](./references/paginated-reports.md) - RDL upload, export-to-file, datasources, parameters
- [Notebooks](./references/notebooks.md) - Python/PySpark kernels, metadata, cell CRUD, Livy execution, scheduling
- [Workspaces](./references/workspaces.md) - Create, manage, permissions
- [Permissions](./references/permissions.md) - Sharing and distribution, workspace roles, item permissions, apps, embed, B2B, deployment pipeline permissions, licensing and capacity SKUs
- [Deployment Pipelines](./references/deployment-pipelines.md) - CI/CD, deploy stages, selective deploy, LRO polling
- [Dataflows](./references/dataflows.md) - Gen1 and Gen2, refresh, publish, admin
- [Dashboards](./references/dashboards.md) - Tiles, clone (dashboards are not reports)
- [Org Apps](./references/org-apps.md) - Read-only API for distributed content packages
- [Scorecards](./references/scorecards.md) - Goals, check-ins, status rules (Preview API)
- [Gateways](./references/gateways.md) - Datasources, credentials, dataset binding
- [Folders](./references/folders.md) - Organize items into folders via API; includes best practices for structuring workspaces
- [Tags](./references/tags.md) - Create, apply, and audit tenant/domain tags on items and workspaces via `fab api` (no native `fab tag` command)
- [fab vs az CLI](./references/fab-vs-az-cli.md) - When to use which; capacity, networking, Key Vault, monitoring, CMK, CI/CD
- [Admin APIs](./references/admin.md) - Cross-workspace search, tenant operations, governance
- [API Reference](./references/fab-api.md) - Capacities, domains, misc API patterns
- [Connections](./references/connections.md) - Create, update, list connections programmatically; credential types (WorkspaceIdentity, SPN, Basic); OAuth2 limitations
- [Service Principals](./references/service-principals.md) - Create an SP with az CLI, grant it workspace access, clear the tenant-setting gate, authenticate `fab` as it (real login vs env-token testing), rotation and teardown
- [Full Command Reference](./references/reference.md) - All commands detailed

**Scripts** (scripts that you can execute):

- [search_across_workspaces.py](./scripts/search_across_workspaces.py) ; cross-workspace governance complement to `fab find` (last visit, last refresh, owner, storage mode, capacity SKU, Copilot readiness); see [workspaces.md](./references/workspaces.md#cross-workspace-search) for when to choose which
- [get-downstream-reports.py](./scripts/get-downstream-reports.py) ; find all reports connected to a given semantic model across accessible workspaces (no admin required)
- [execute_dax.py](./scripts/execute_dax.py) ; execute DAX queries against semantic models; output as table, csv, or json
- [query_lakehouse_duckdb.py](./scripts/query_lakehouse_duckdb.py) ; query lakehouse or warehouse Delta tables via DuckDB against OneLake (reuses `az login`); output as table, csv, or json
- [query_sql_endpoint.py](./scripts/query_sql_endpoint.py) ; query lakehouse SQL endpoint, warehouse, or SQL database via `sqlcmd` (reuses `az login` through `ActiveDirectoryAzCli`); output as table, csv, or json
- [create_direct_lake_model.py](./scripts/create_direct_lake_model.py) ; create a Direct Lake semantic model from lakehouse tables
- [download_workspace.py](./scripts/download_workspace.py) ; download a full workspace with all item definitions and lakehouse files
- [run_notebook_checked.py](./scripts/run_notebook_checked.py) ; run a notebook and check its exit value, exiting non-zero when the notebook's own `{ok:false}` verdict fails despite a `Completed` job status (reads the exit value via the notebook job-instance beta endpoint)
- [deploy_notebook.py](./scripts/deploy_notebook.py) ; create or update a notebook definition fast (~1-2s) by tight-polling the LRO instead of the CLI's ~20s `Retry-After` cadence; auto-detects create vs update, `--poll-interval` is the performance lever. Strongly prefer this over `fab import` / `nb` for any notebook definition change

See [scripts/README.md](./scripts/README.md) for detailed usage, arguments, and examples. Always search the `scripts/` folder before writing a new helper; a script may already exist for the task.

**External references** (request markdown when possible):

- fab CLI: [GitHub Source](https://github.com/microsoft/fabric-cli) | [Docs](https://microsoft.github.io/fabric-cli/)
- Microsoft: [Fabric CLI Learn](https://learn.microsoft.com/en-us/rest/api/fabric/articles/fabric-command-line-interface)
- APIs: [Fabric API](https://learn.microsoft.com/en-us/rest/api/fabric/articles/) | [Power BI API](https://learn.microsoft.com/en-us/rest/api/power-bi/)
- DAX: [dax.guide](https://dax.guide/) - use `dax.guide/<function>/` e.g. `dax.guide/addcolumns/`
- Power Query: [powerquery.guide](https://powerquery.guide/) - use `powerquery.guide/function/<function>`
- [Power Query Best Practices](https://learn.microsoft.com/en-us/power-query/best-practices)
