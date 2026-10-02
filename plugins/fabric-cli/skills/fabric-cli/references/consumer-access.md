# Why a consumer sees no data

A consumer who can open a report but gets an error or empty visuals is almost never missing a
workspace role. Each cause below surfaces as a vague error far from where it starts, so check them in
this order before granting anything bigger. The permission model itself is in
[permissions.md](./permissions.md).

## 1. A query path that is not a Power BI report needs Build

A workspace **Viewer** can open a Power BI report, but anything that runs DAX against the semantic
model directly (the `executeQueries` REST endpoint, a Fabric App, a custom front end) fails with
"database does not exist or you do not have permissions" until the user also has **Build** on the
model: Manage permissions, Direct access, then Add build. Build does **not** bypass RLS.

## 2. Once any RLS role exists, a user in no role sees nothing

When a model has at least one RLS role, a Viewer who is a member of none is denied entirely. A report
says it "can't be viewed because the underlying dataset uses RLS"; a Fabric App or API caller gets the
same misleading "database does not exist" error as above. The fix is role **membership**, not a
sharing change.

- Role membership (users and groups per role) lives **only in the service**: semantic model, More
  options, Security. It is never in the PBIP and never visible in Desktop, and it survives a
  republish as long as the role names are unchanged.
- Write holders (workspace Admin, Member, Contributor) bypass RLS, which is why the model owner never
  sees the failure. See [permissions.md](./permissions.md).

## 3. An RLS role whose filters intersect to nothing

Before specifying rules on two dimensions, count the rows the intersection keeps. A role filtering a
vendor group and a division can be perfectly valid and match zero fact rows, because that vendor
group never sells to that division. An empty role renders an honest "No data", which is easily read as
a bug. Count with a DAX query that applies both filters before shipping the rule.

## 4. Direct Lake on SQL checks the consumer's own identity

A Direct Lake model on a SQL endpoint (`Sql.Database("<host>", "<sqlEndpointId>")`) that is **not
bound to a cloud connection** uses single sign-on: every query runs as the report consumer. A
lakehouse's stock `DefaultReader` OneLake role admits "anyone with ReadAll", and a workspace **Viewer
gets neither OneLake read nor ReadAll** (Contributor and above get it implicitly). So a Viewer sees
"You don't have permission to view the content of Direct Lake table" on every visual. With
`directLakeBehavior: directLakeOnly` there is no DirectQuery fallback, so it is a hard error rather
than a slow query.

**Fix with a fixed identity, not a bigger role:**

1. Create a shareable cloud connection to the SQL endpoint with `credentialType: WorkspaceIdentity`
   (or a service principal) and **`singleSignOnType: None`**.
2. Bind each Direct Lake model to it (see [gateways.md](./gateways.md) for binding).
3. Publish an app and give consumers app access only. Least privilege is then app access alone: no
   workspace role, no lakehouse permission.

Leaving SSO **on** beside a fixed identity does not fix it: Direct Lake still checks the current user
at query time and uses the fixed identity only for framing. SSO must be off.

Two traps in the binding:

- **Datasource matching is literal.** An existing connection whose path names the SQL database by
  **name** does not match a Direct Lake model that references the endpoint by **GUID**; create one
  whose path carries the GUID.
- **`Default.GetBoundGatewayDatasources` returns `[]` even when a Direct Lake model is bound.** Verify
  with `GET groups/{ws}/datasets/{id}/datasources` and look for `datasourceId` and `gatewayId` on the
  row instead.
- The binding survives a later `updateDefinition` of the model (adding a table, August 2026), so a
  definition change does not need a re-bind.

The trade-off: every query now runs as one shared identity, so everyone in the app audience sees the
whole dataset unless the model applies RLS. That is also the precondition for model RLS to mean
anything on Direct Lake.

(Diagnosed and fixed in a tenant, July 2026.)
