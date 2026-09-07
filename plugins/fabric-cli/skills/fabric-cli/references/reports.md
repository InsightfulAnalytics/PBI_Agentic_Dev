# Report Operations

## Get Report Info

```bash
# Check exists
fab exists "ws.Workspace/Report.Report"

# Get properties
fab get "ws.Workspace/Report.Report"

# Get ID
fab get "ws.Workspace/Report.Report" -q "id"
```

## Get Report Definition

```bash
# Full definition
fab get "ws.Workspace/Report.Report" -q "definition"

# Save to file
fab get "ws.Workspace/Report.Report" -q "definition" -o /tmp/report-def.json

# Specific parts
fab get "ws.Workspace/Report.Report" -q "definition.parts[?path=='definition/report.json'].payload | [0]"
```

## Get Connected Model

```bash
# Get model reference from definition.pbir
fab get "ws.Workspace/Report.Report" -q "definition.parts[?contains(path, 'definition.pbir')].payload | [0]"
```

Output shows `byConnection.connectionString` with `semanticmodelid`.

## Export Report

1. Export to local directory:

```bash
fab export "ws.Workspace/Report.Report" -o /tmp/exports -f
```

2. Creates structure:

```
Report.Report/
├── .platform
├── definition.pbir
└── definition/
    ├── report.json
    ├── version.json
    └── pages/
        └── {page-id}/
            ├── page.json
            └── visuals/{visual-id}/visual.json
```

## Import Report

1. Import from local PBIP:

```bash
fab import "ws.Workspace/Report.Report" -i /tmp/exports/Report.Report -f
```

2. Import with new name:

```bash
fab import "ws.Workspace/NewName.Report" -i /tmp/exports/Report.Report -f
```

## Copy Report Between Workspaces

```bash
fab cp "dev.Workspace/Report.Report" "prod.Workspace" -f
```

## Create Blank Report

1. Get model ID:

```bash
fab get "ws.Workspace/Model.SemanticModel" -q "id"
```

2. Create report:

```bash
# Native alternative (preferred):
fab mkdir "ws.Workspace/New Report.Report"

# Via API:
WS_ID=$(fab get "ws.Workspace" -q "id" | tr -d '"')
fab api -X post "workspaces/$WS_ID/reports" -i '{
  "displayName": "New Report",
  "datasetId": "<model-id>"
}'
```

## Update Report Properties

```bash
# Rename
fab set "ws.Workspace/Report.Report" -q displayName -i "New Name"

# Update description
fab set "ws.Workspace/Report.Report" -q description -i "Description text"
```

## Rebind to Different Model

1. Get new model ID:

```bash
fab get "ws.Workspace/NewModel.SemanticModel" -q "id"
```

2. Rebind:

```bash
fab set "ws.Workspace/Report.Report" -q semanticModelId -i "<new-model-id>"
```

## Delete Report

```bash
fab rm "ws.Workspace/Report.Report" -f
```

Recovery depends on the tenant Item Recovery setting; see [reference.md > Recovering deleted items](reference.md#recovering-deleted-items).

## List Pages

```bash
fab get "ws.Workspace/Report.Report" -q "definition.parts[?contains(path, 'page.json')].path"
```

## List Visuals

```bash
fab get "ws.Workspace/Report.Report" -q "definition.parts[?contains(path, '/visuals/')].path"
```

## Count Visuals by Type

1. Export visuals:

```bash
fab get "ws.Workspace/Report.Report" -q "definition.parts[?contains(path,'/visuals/')]" > /tmp/visuals.json
```

2. Count by type:

```bash
jq -r '.[] | .payload.visual.visualType' < /tmp/visuals.json | sort | uniq -c | sort -rn
```

## Extract Fields Used in Report

1. Export visuals (if not done):

```bash
fab get "ws.Workspace/Report.Report" -q "definition.parts[?contains(path,'/visuals/')]" > /tmp/visuals.json
```

2. List unique fields:

```bash
jq -r '[.[] | (.payload.visual.query.queryState // {} | to_entries[] | .value.projections[]? | if .field.Column then "\(.field.Column.Expression.SourceRef.Entity).\(.field.Column.Property)" elif .field.Measure then "\(.field.Measure.Expression.SourceRef.Entity).\(.field.Measure.Property)" else empty end)] | unique | sort | .[]' < /tmp/visuals.json
```

## Validate Fields Against Model

1. Export report:

```bash
fab export "ws.Workspace/Report.Report" -o /tmp/report -f
```

2. Extract field references:

```bash
find /tmp/report -name "visual.json" -exec grep -B2 '"Property":' {} \; | \
  grep -E '"Entity":|"Property":' | paste -d' ' - - | \
  sed 's/.*"Entity": "\([^"]*\)".*"Property": "\([^"]*\)".*/\1.\2/' | sort -u
```

3. Compare against model definition to find missing fields.

## Report Permissions

1. Get IDs:

```bash
WS_ID=$(fab get "ws.Workspace" -q "id" | tr -d '"')
REPORT_ID=$(fab get "ws.Workspace/Report.Report" -q "id" | tr -d '"')
```

2. List users:

```bash
# Native alternative (preferred):
fab acl ls "ws.Workspace/Report.Report"

# Via API:
fab api -A powerbi "groups/$WS_ID/reports/$REPORT_ID/users"
```

3. Add user:

```bash
# Native alternative (preferred):
fab acl set "ws.Workspace/Report.Report" -I <objectId> -R Viewer

# Via API:
fab api -A powerbi "groups/$WS_ID/reports/$REPORT_ID/users" -X post -i '{
  "emailAddress": "user@domain.com",
  "reportUserAccessRight": "View"
}'
```

## Deploy Report (Dev to Prod)

1. Export from dev:

```bash
fab export "dev.Workspace/Report.Report" -o /tmp/deploy -f
```

2. Import to prod:

```bash
fab import "prod.Workspace/Report.Report" -i /tmp/deploy/Report.Report -f
```

3. Verify:

```bash
fab exists "prod.Workspace/Report.Report"
```

## Clone Report with Different Model

1. Download and copy the source:

```bash
pbir download "ws.Workspace/Template.Report" -o /tmp/clone --format pbir
pbir cp "/tmp/clone/Template.Report" "/tmp/clone/NewReport.Report"
```

2. Rebind the copy:

```bash
pbir report rebind "/tmp/clone/NewReport.Report" \
  "ws.Workspace/NewModel.SemanticModel"
pbir validate "/tmp/clone/NewReport.Report" --all
```

3. Publish as a new report:

```bash
pbir publish "/tmp/clone/NewReport.Report" "ws.Workspace/NewReport.Report"
```

## Troubleshooting

### Report Not Found

```bash
fab exists "ws.Workspace"
fab ls "ws.Workspace" | grep -i report
```

### Model Binding Issues

```bash
# Check current binding
fab get "ws.Workspace/Report.Report" -q "definition.parts[?contains(path, 'definition.pbir')].payload | [0]"

# Rebind
fab set "ws.Workspace/Report.Report" -q semanticModelId -i "<model-id>"
```

### Import Fails

```bash
# Verify structure
ls -R /tmp/exports/Report.Report/

# Check definition is valid JSON
fab get "ws.Workspace/Report.Report" -q "definition" | jq . > /dev/null && echo "Valid"
```

## Server-side render for headless visual verification

Where Power BI Desktop is unavailable (a Linux Codespace, CI, a container) or its local screenshot API cannot be reached, the service will render the report instead. This is the substitute for a Desktop screenshot loop, and the only way to actually see a published report from a machine with no Desktop.

Same three steps as a paginated export, against a Power BI report:

1. `POST groups/{ws}/reports/{id}/ExportTo` with `{"format":"PDF"}` ; [Step 1](./paginated-reports.md#step-1-initiate-export)
2. Poll `.../exports/{eid}` until `Succeeded` ; [Step 2](./paginated-reports.md#step-2-poll-export-status)
3. `GET .../exports/{eid}/file` ; [Step 3](./paginated-reports.md#step-3-download-exported-file)

It works on trial capacity, and it renders certified custom visuals, Deneb included, so it is a genuine visual check rather than a layout dump.

Two mechanics decide whether the loop works at all:

- **Fetch the file over raw HTTP, not `fab api`.** `fab api` wraps every response in a JSON envelope and corrupts binary bodies, so the PDF arrives unreadable and nothing complains until something tries to open it. Use a bearer token from `az account get-access-token --resource https://analysis.windows.net/powerbi/api`. See [fab-api.md](./fab-api.md#binary-bodies-must-not-go-through-fab-api).
- **Convert the PDF to PNG with `pymupdf`** (`pip install pymupdf`). It is pure pip with no system dependency, so it works where `pdftoppm` does not because poppler is not installed.

```bash
TOKEN=$(az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.powerbi.com/v1.0/myorg/groups/$WS_ID/reports/$REPORT_ID/exports/$EXPORT_ID/file" \
  -o report.pdf

python3 -c "
import pymupdf
doc = pymupdf.open('report.pdf')
for i, page in enumerate(doc):
    page.get_pixmap(dpi=150).save(f'page-{i+1}.png')
"
```

`format: "PNG"` is also accepted for Power BI reports and skips the conversion, but PDF is the format with the widest visual fidelity across visual types.
