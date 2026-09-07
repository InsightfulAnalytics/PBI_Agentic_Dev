# Connections API

Programmatically create, update, list, and delete Fabric cloud connections.

## List Connections

```bash
fab ls .connections -l
```

Or via API:

```
GET https://api.fabric.microsoft.com/v1/connections
```

## Create Connection

```
POST https://api.fabric.microsoft.com/v1/connections
```

### With WorkspaceIdentity (no secrets needed)

```json
{
  "connectivityType": "ShareableCloud",
  "displayName": "MyLakehouseConnection",
  "connectionDetails": {
    "type": "SQL",
    "creationMethod": "SQL",
    "parameters": [
      {"dataType": "Text", "name": "server", "value": "<endpoint>.datawarehouse.fabric.microsoft.com"},
      {"dataType": "Text", "name": "database", "value": "<LakehouseName>"}
    ]
  },
  "privacyLevel": "Organizational",
  "credentialDetails": {
    "singleSignOnType": "None",
    "connectionEncryption": "Encrypted",
    "skipTestConnection": false,
    "credentials": {
      "credentialType": "WorkspaceIdentity"
    }
  }
}
```

WorkspaceIdentity uses the workspace's managed service principal. No passwords, secrets, or OAuth consent. Supported for Fabric data sources (SQL, ADLS connectors).

The identity must exist and hold rights on the source before this succeeds: provision it with `POST workspaces/{ws}/provisionIdentity`, then grant it a data role on the target (for example Storage Blob Data Reader on a storage account). For an ADLS Gen2 source use `"type": "AzureDataLakeStorage"`, `"creationMethod": "AzureDataLakeStorage"` and the parameters `server=https://<acct>.dfs.core.windows.net` and `path=<container>`. Full non-interactive shortcut chain: [lakehouses.md > Headless ADLS Gen2 shortcut, end to end](./lakehouses.md#headless-adls-gen2-shortcut-end-to-end).

### With Basic Auth

```json
{
  "connectivityType": "ShareableCloud",
  "displayName": "MyConnection",
  "connectionDetails": {
    "type": "SQL",
    "creationMethod": "SQL",
    "parameters": [
      {"dataType": "Text", "name": "server", "value": "myserver.database.windows.net"},
      {"dataType": "Text", "name": "database", "value": "mydb"}
    ]
  },
  "privacyLevel": "Organizational",
  "credentialDetails": {
    "singleSignOnType": "None",
    "connectionEncryption": "NotEncrypted",
    "skipTestConnection": false,
    "credentials": {
      "credentialType": "Basic",
      "username": "admin",
      "password": "********"
    }
  }
}
```

### With Service Principal

```json
{
  "credentialDetails": {
    "credentials": {
      "credentialType": "ServicePrincipal",
      "servicePrincipalClientId": "<client-id>",
      "servicePrincipalSecret": "<secret>",
      "tenantId": "<tenant-id>"
    }
  }
}
```

## Supported Credential Types

| Type | API Support | Notes |
|------|------------|-------|
| WorkspaceIdentity | Yes | No secrets; uses workspace managed identity |
| Basic | Yes | Username + password |
| ServicePrincipal | Yes | Client ID + secret + tenant |
| Key | Yes | API key or account key |
| SharedAccessSignature | Yes | SAS token |
| Anonymous | Yes | No credentials |
| OAuth2 | **No** | Requires browser consent; cannot be created via API |
| Windows | No | On-premises gateway only |

## Update Connection

```
PATCH https://api.fabric.microsoft.com/v1/connections/{connectionId}
```

Update display name or credential details. Cannot change credential type (e.g. OAuth2 to WorkspaceIdentity).

Via `fab`:

```bash
fab set ".connections/<Name>.Connection" -q displayName -i "New Name"
fab set ".connections/<Name>.Connection" -q credentialDetails -i @creds.json
```

The display-name form is routine. The `credentialDetails` form is not confirmed working; for a credential change, use the `fab api` PATCH below, which is the verified route.

### Updating credentials to a service principal

The verified route is `fab api` against the connection id, with the body in a file:

```bash
fab api -X patch "connections/<id>" -i body.json
```

`body.json` carries `credentialDetails.credentials.credentialType` `ServicePrincipal` plus `servicePrincipalClientId`, `servicePrincipalSecret` and `tenantId`, as in the create example above.

**`WebForPipeline` (Web v2) connections reject `skipTestConnection: true`** with `SkipTestConnectionNotSupported`, so the body must send `skipTestConnection: false` and the credentials are **live-tested at save time**. That cuts both ways:

- A successful PATCH proves the service principal can actually reach the endpoint, not merely that the fields were accepted.
- A failing PATCH has three possible causes, not one: a wrong credential, a secret that has not propagated yet (see [service-principals.md](./service-principals.md#gotchas)), or a target the SP cannot reach. Retry once after a minute before treating it as a bad secret.

## Delete Connection

```
DELETE https://api.fabric.microsoft.com/v1/connections/{connectionId}
```

Via `fab`:

```bash
fab rm ".connections/<Name>.Connection" -f
```

## Get Connection Details

```bash
fab get .connections/<ConnectionName>.Connection
fab get .connections/<ConnectionName>.Connection -q "connectionDetails"
```

## Key Limitation: OAuth2 Connections

OAuth2 connections **cannot be created or refreshed via API**. They require an interactive browser OAuth consent flow. This affects:

- Dataflow `executeQuery` API: needs OAuth-authenticated connections for data source access
- Semantic model refresh: needs OAuth connections for cloud data sources

**Workarounds:**
- Use `WorkspaceIdentity` or `ServicePrincipal` credential types instead of OAuth2
- For OAuth2: create the connection once in the portal, then reference it by ID in automation
- Use `fab` CLI connections management: `fab ls .connections`, `fab get .connections/Name.Connection`

## Microsoft Documentation

- [Create Connection API](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/create-connection)
- [Update Connection API](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/update-connection)
- [List Connections API](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/list-connections)
- [Data Source Management](https://learn.microsoft.com/en-us/fabric/data-factory/data-source-management)
