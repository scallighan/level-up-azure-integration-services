# Lab 1 implementation requirements

Build one lookup-and-transform workflow, not a CRUD API or website. Read the
[README](README.md), [OpenAPI contract](contracts/openapi.yaml),
[sample data](contracts/regions.json),
[implementation standards](../../docs/implementation-standards.md), and
[Logic App Standard baseline](../../docs/logic-app-standard-baseline.md).

## Resource responsibilities

Complete Lab 0 first. Use `foundation.deployment.json` as the explicit handoff.
Both Bicep and Terraform learners must produce the same behavior.

| Resource | Lab 1 responsibility |
|---|---|
| Parent group, site, hosting, networking, storage, monitoring | Reference Lab 0; do not import, retag, replace, or manage these resources |
| Cosmos DB | Use the existing private, Entra-only account and `workshop/items`, partition key `/id` |
| Cosmos authorization | Reuse the site's existing container-scoped system-identity grant |
| Workflow | Add only `region-lookup`, with an HTTP request trigger and synchronous JSON response |
| Connection | Reuse the seed script's `lab01Cosmos` built-in connection |
| Website, API Management, new backend resources | None |

The user-assigned identity remains host-storage-only. Use the system-assigned
identity for Cosmos access. Do not enable public Cosmos access, use account
keys, or grant the workstation additional Cosmos data-plane roles.

## Lookup data

`contracts/regions.json` is a small teaching snapshot of the programmatic names
and physical locations in Microsoft's
[Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list?tabs=all),
checked on October 19, 2026. It is not a complete or live Azure region catalog.
Use these public sample values, not customer system names or cross-reference data.

Each document has this shape:

```json
{
  "id": "lab01-region-westus",
  "programmaticName": "westus",
  "physicalLocation": "California"
}
```

`id` is also the partition-key value. Look up
`concat('lab01-region-', <programmaticName>)` with `ReadDocument`, passing that
same value as `itemId` and `partitionKey`. Do not query across partitions,
call the region-list website at runtime, or copy lookup values into the workflow.

`scripts/seed-region-lookups.py` supplies the data, not the learner's solution.
It uses a uniquely named temporary workflow in the existing VNet-integrated
site to upsert only these document IDs. It preserves existing connections,
uses the site's system identity, checks the run result, and removes its
temporary workflow on success or failure. The `lab01Cosmos` entry remains
for the learner. No callback URL or account key is needed by the seed script.
Do not run simultaneous artifact deployments while seeding.

## Request, transformation, and response

Treat `contracts/openapi.yaml` as the source of truth.
`POST /region-lookup` describes the operation; the deployed workflow uses its
HTTP trigger callback URL, not an API gateway route.

1. Accept a JSON object with exactly one required string, `programmaticName`.
   It must be 2-40 lowercase letters or digits, starting with a letter.
   Do not silently trim, lowercase, substitute, or default invalid values.
2. Read the matching document from Cosmos DB. This workflow is read-only.
3. Return HTTP `200`, `Content-Type: application/json`, and exactly
   `programmaticName` and `physicalLocation`.

Return deliberate JSON errors containing only `code` and `message`:

| Status | Code | Meaning |
|---|---|---|
| `400` | `InvalidRequest` | Malformed JSON, missing/invalid field, or extra fields |
| `404` | `RegionNotFound` | No seeded document for the supplied name |
| `503` | `LookupUnavailable` | Cosmos read failed for a reason other than not found |
| `500` | `InternalError` | Unexpected transformation or workflow failure |

Catch validation failures inside the workflow so they produce the contracted
error envelope. Do not let an overly restrictive trigger schema bypass that
handling. An HTTP response must exist for each handled path; never return
partial data or a successful response on a failed lookup. A repeated request
must produce the same response without changing any documents.

Use two fixed read retries at `PT5S`, followed by the explicit error response.
Read connector errors from `actions('<read-action>').code`; `NotFound` maps
to `404`. Do not assume a ServiceProvider action has `outputs.statusCode`.
Keep the response within the synchronous HTTP window; do not introduce polling
or long-running work into this read-only transformation.

Do not return `_rid`, `_self`, `_etag`, `_attachments`, `_ts`, connector
diagnostics, failure bodies, or the document ID. Do not record full request
or response payloads in run history; secure trigger and data-action inputs
and outputs. Use run IDs for diagnosis, not payload logging.

## Workflow artifacts and connection

Deploy Standard artifacts through the site's `deployWorkflowArtifacts`
operation. The files map contains `region-lookup/workflow.json`; preserve every
other workflow. Do not `PUT` to `Microsoft.Web/sites/workflows`.

The seed script creates this `serviceProviderConnections` entry in the shared
`connections.json`:

```json
{
  "lab01Cosmos": {
    "displayName": "Lab 1 region lookup",
    "parameterSetName": "ManagedServiceIdentity",
    "parameterValues": {
      "accountURI": "@appsetting('AzureCosmosDB_accountEndpoint')"
    },
    "serviceProvider": {
      "id": "/serviceProviders/AzureCosmosDB"
    },
    "authProvider": {
      "Type": "ManagedServiceIdentity"
    }
  }
}
```

Reference it using `connectionName: lab01Cosmos`. For `ReadDocument`,
`inputs.parameters` contains `databaseId`, `containerId`, `itemId`, and
`partitionKey`. Put `retryPolicy` under the action's `inputs`, not beside them.
The built-in `ReadDocument` result contains the document as a JSON string in
`content`. Parse that string before projecting the two response fields.

Do not replace the site's full settings or connection file. If an artifact
deployment needs to update connections, read the current file and merge only
the required entry. Terraform may use `azapi_resource_action` for
`deployWorkflowArtifacts`, with that reason documented; Bicep must use the
same supported artifact operation through its deployment tooling.

## Validation and cleanup

Verify Lab 0's readiness first if it has changed. Before deploying, validate
workflow/connection JSON and review the selected track's format/build/preview
or fmt/validate/plan. The preview must have no foundation writes.

Test every case in `contracts/test-cases.json`, compare the successful response
with `sample-response.json`, and inspect a run to prove an actual Cosmos read.
A different seeded name must return its own physical location. Check the
unavailable-store error path without weakening networking or RBAC.

Retrieve the callback URL privately for the exercise only. Never commit,
output in IaC, log, or persist it. There is no browser/CORS task in this lab.

Cleanup removes `region-lookup` and only its unused connection entry. Verify
artifact removal explicitly; Terraform state destruction alone may leave
uploaded files. Keep the sample documents until Lab 0 cleanup, and preserve
all other labs' artifacts and the shared foundation.
