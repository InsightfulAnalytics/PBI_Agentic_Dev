# Usage telemetry and lineage: what the APIs do not give

Where report-page usage and item lineage actually live, and the gaps every tenant-wide harvest hits.
The admin and Scanner API mechanics are in [admin.md](./admin.md); `pbir usage` (reports plugin,
`pbir-cli` `references/cli-reference.md`, Usage Metrics) reads the same telemetry for one report.

(Established in a tenant between July and September 2026, against the documented APIs plus live
queries.)

## Report-page views exist only in the usage metrics models

Page-level view counts are in the per-workspace **usage metrics** semantic models and nowhere else.
Dead ends, each checked: the activity log and Purview (no page property on any event), the admin
monitoring models (report level only), Microsoft Graph (no Power BI usage endpoints), and Scanner
results.

- A workspace has up to two hidden usage models: the legacy **Report Usage Metrics Model**, whose
  `'Views'` table carries `ReportPage` (the page display name), and the modern **Usage Metrics
  Report**, whose `'Report page views'` joins `SectionId` to `'Report pages'[SectionName]`. One
  workspace's modern table stayed empty while its legacy table had rows, and other workspaces were
  the other way round, so a harvest reads **both**.
- A workspace gets its models only when someone opens **View usage metrics** in the Service once.
  No API creates them. They keep 30 days and refresh daily; schedule any harvest after that refresh,
  or it is always a day stale.
- **Page views are client telemetry; report views are server-side.** A gap in page views with report
  views present can be an ad blocker or web shield dropping the client events, or simply nobody
  having viewed a multi-page report.
- Both models answer `executeQueries` with **one `EVALUATE` per POST**. `INFO.VIEW.TABLES()` works
  there; `INFO.TABLES()` is rejected.
- A server-side proxy that ad blockers cannot drop: Workspace Monitoring (or Log Analytics) `QueryEnd`
  events carry `ApplicationContext.Sources[0]` with `ReportId` and `VisualId`, and `VisualId` is the
  PBIR visual folder name, so `pages/<page>/visuals/<VisualId>/` maps a query to its page. It is a
  proxy only: caching undercounts, and a page with no queries is invisible.

Notebook gotcha when harvesting with semantic link: `COUNTROWS` over an empty table comes back as
`pd.NA` (nullable `Int64`), and `pd.NA or 0` raises "boolean value of NA is ambiguous". Guard every
scalar with `pd.isna` before using it in a condition.

## Lineage the Scanner API does not return

The Scanner API gives report to model, report to app, model to dataflow (with `groupId`, so cross
workspace works), model and dataflow to datasource, dataflow to dataflow, and datasource detail. It
does not give three things:

1. **Direct Lake and default semantic models return no `datasourceUsages` at all.** Recover the source
   by reading the model definition (`GET /v1/workspaces/{ws}/semanticModels/{id}/getDefinition`) and
   parsing `Sql.Database("<host>", "<sqlEndpointId>")` from its expressions.
2. **A Fabric SQL host encodes its workspace.** The host is
   `<cluster>-<base32 of the workspace GUID's little-endian bytes>.datawarehouse.fabric.microsoft.com`,
   so the workspace GUID is decodable from the host alone, and OneLake URLs resolve back to their
   lakehouse the same way.
3. **Model to model** (`upstreamDatasets`) is in the API response but easy to drop when flattening;
   keep it. Notebook and pipeline to lakehouse lineage is exposed by **no** admin API.

A scan that returns models with no tables or expressions is the security-group scoping covered in
[admin.md](./admin.md), Scanner gotchas (`DatasetSchemaDisabledByAdmin`).

## Capacity cost per report

Fabric books **zero CU against Report items**. Report-level cost is always an allocation (the model's
query CU times the report's share of views), never a measurement; say so whenever a report-level cost
is shown. Querying the Capacity Metrics app's model is in [admin.md](./admin.md).
