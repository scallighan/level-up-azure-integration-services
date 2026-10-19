# Lab 1 implementation requirements

Build one lookup-and-transform workflow, not a CRUD API or website. Read the
[README](README.md), [OpenAPI contract](contracts/openapi.yaml),
[region data](contracts/regions.json), [support-tier data](contracts/support-tiers.json),
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
| Workflow | Add only `lab01-workflow`, with an HTTP request trigger and synchronous JSON response |
| Connection | Reuse the seed script's `lab01Cosmos` built-in connection |
| Website, API Management, new backend resources | None |

The user-assigned identity remains host-storage-only. Use the system-assigned
identity for Cosmos access. Do not enable public Cosmos access, use account
keys, or grant the workstation additional Cosmos data-plane roles.

## Lookup data

`contracts/regions.json` is a small teaching snapshot of the programmatic names,
region display names, and physical locations in Microsoft's
[Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list?tabs=all),
checked on October 19, 2026. It is not a complete or live Azure region catalog.
Use these public sample values, not customer system names or cross-reference data.

Each document has this shape:

```json
{
  "id": "lab01-region-westus",
  "programmaticName": "westus",
  "displayName": "West US",
  "physicalLocation": "California"
}
```

`id` is also the partition-key value. Look up
`concat('lab01-region-', <programmaticName>)` with `ReadDocument`, passing that
same value as `itemId` and `partitionKey`. Do not query across partitions,
call the region-list website at runtime, or copy lookup values into the workflow.

`contracts/support-tiers.json` contains three synthetic, non-region lookup
records. These are fictional teaching values, not Azure support plans or
service commitments:

```json
{
  "id": "lab01-support-standard",
  "supportTier": "standard",
  "displayName": "Standard",
  "responseTimeHours": 8
}
```

Look up `concat('lab01-support-', <supportTier>)` with `ReadDocument`, again
using the ID as both `itemId` and `partitionKey`. The keys `basic`, `standard`,
and `priority` are independent of region and can be combined with any seeded
region. Keep `responseTimeHours` a positive integer.

`scripts/prepare-lab1.py` prepares the data and connection, not the learner's solution.
It uses a uniquely named temporary workflow in the existing VNet-integrated
site to upsert only the six region IDs and three support-tier IDs. It preserves existing connections,
uses the site's system identity, checks the run result, and removes its
temporary workflow on success or failure. The `lab01Cosmos` entry remains
for the learner. No callback URL or account key is needed by the seed script.
Do not run simultaneous artifact deployments while seeding.

The helper follows the repository-wide `show_sample_payloads=true` default.
Omit data-action protection blocks so its public seed inputs/outputs are
visible; `--no-show-sample-payloads` explicitly selects protected helper history.

With `--keep-workflow`, retain the helper and its run history on success or
failure instead. Disable only that helper using the
`Workflows.<name>.FlowState=Disabled` app setting, merging without removing any
other settings and verifying the saved value. This prevents scheduled reseeding.
Changing app settings can restart the shared site; use this debugging option
between other lab tests. Never print the site's full settings or secrets.
Report retention/disable failures explicitly, preserving the original seed error.
After debugging, remove the retained helper and its workflow-specific setting.

## Request, transformation, and response

Treat `contracts/openapi.yaml` as the source of truth.
`POST /region-lookup` describes the logical operation; the deployed workflow
is named `lab01-workflow` and uses its HTTP trigger callback URL, not an API
gateway route. Changing the workflow name changes its callback URL, not this
logical contract path.

1. Accept exactly the five fields defined in the contract. `requestId` and
   `workloadName` are nonempty strings, `instanceCount` is a positive integer,
   and `programmaticName` and `supportTier` must each be 2-40 lowercase
   letters or digits, starting with a letter. Output fields are not accepted
   in the request.
   Do not silently trim, lowercase, substitute, or default invalid values.
2. Read the region document, then the independent support-tier document from
   Cosmos DB. This workflow is read-only. If the region is missing, return
   `RegionNotFound` without reading support; if support is missing, return
   `SupportTierNotFound`. Never return a partial success.
3. Return HTTP `200`, `Content-Type: application/json`, and exactly nine fields,
   following this mapping:

| Response field | Source |
|---|---|
| `requestId` | Copy from the request unchanged |
| `workloadName` | Copy from the request unchanged |
| `instanceCount` | Copy from the request as an integer, not a string |
| `programmaticName` | Copy the validated lookup key unchanged |
| `supportTier` | Copy the validated lookup key unchanged |
| `regionDisplayName` | Add the region document's `displayName` |
| `physicalLocation` | Add the region document's `physicalLocation` |
| `supportTierDisplayName` | Add the support-tier document's `displayName` |
| `responseTimeHours` | Add the support-tier document's positive integer, not a string |

The request supplies only lookup keys and pass-through metadata, not output
placeholders. Do not default a missing or failed lookup. A region document
missing valid nonempty `displayName` or `physicalLocation`, or a support-tier
document missing a valid nonempty `displayName` or positive integer
`responseTimeHours`, is an `InternalError`, not a successful partial response.
This is a payload transformation; do not provision the requested workload.

Return deliberate JSON errors containing only `code` and `message`:

| Status | Code | Meaning |
|---|---|---|
| `400` | `InvalidRequest` | Malformed JSON, missing/invalid field, or extra fields |
| `404` | `RegionNotFound` | No seeded document for the supplied name |
| `404` | `SupportTierNotFound` | No seeded document for the supplied support tier |
| `503` | `LookupUnavailable` | Cosmos read failed for a reason other than not found |
| `500` | `InternalError` | Unexpected transformation or workflow failure |

Catch validation failures inside the workflow so they produce the contracted
error envelope. Do not let an overly restrictive trigger schema bypass that
handling. An HTTP response must exist for each handled path; never return
partial data or a successful response on a failed lookup. A repeated request
must produce the same response without changing any documents.

Use two fixed retries at `PT5S` for each read, followed by the explicit error response.
Read connector errors from `actions('<read-action>').code`; `NotFound` maps
to `404`. Do not assume a ServiceProvider action has `outputs.statusCode`.
Keep the response within the synchronous HTTP window; do not introduce polling
or long-running work into this read-only transformation.

Do not return `_rid`, `_self`, `_etag`, `_attachments`, `_ts`, connector
diagnostics, failure bodies, or the document ID. Show the public teaching
payloads in run history by default. Before using real or sensitive data,
disable sample visibility and use the supported secure-data settings below.
Never record secrets or sensitive payloads in run history. Use run IDs for
normal diagnosis.

### Runtime validation guardrails

Standard's `ParseJson` action rejects schemas containing `pattern` or
`patternProperties` with `ActionSchemaNotSupported`, even for valid requests.
A successful JSON/schema check or deployment does not detect this runtime
restriction. Keep the patterns in OpenAPI, but do not copy them into
`ParseJson` schemas or silently drop their validation.

Use native workflow actions, in this order:

1. `Validate_Request`: `ParseJson` with the contract's required fields, types,
   lengths, integer minimum, and `additionalProperties: false`, omitting only
   unsupported pattern keywords.
2. `Lookup_Keys`: `Compose` the two validated strings into this object. Convert
   the object with `xml()`; do not concatenate request text into XML.

   ```json
   {
     "root": {
       "programmaticName": "@body('Validate_Request')['programmaticName']",
       "supportTier": "@body('Validate_Request')['supportTier']"
     }
   }
   ```

3. `Validate_Keys`: use these `ParseJson` inputs to enforce the first-letter
   and allowed-character rules for both keys. Lengths were checked in step 1.
   A false result must fail validation and reach the `400 InvalidRequest`
   response before either Cosmos read.

   ```json
   {
     "content": "@xpath(xml(outputs('Lookup_Keys')), 'boolean(contains(\"abcdefghijklmnopqrstuvwxyz\", substring(/root/programmaticName, 1, 1)) and string-length(translate(/root/programmaticName, \"abcdefghijklmnopqrstuvwxyz0123456789\", \"\")) = 0 and contains(\"abcdefghijklmnopqrstuvwxyz\", substring(/root/supportTier, 1, 1)) and string-length(translate(/root/supportTier, \"abcdefghijklmnopqrstuvwxyz0123456789\", \"\")) = 0)')",
     "schema": {
       "type": "boolean",
       "enum": [true]
     }
   }
   ```

Validate lookup document types and required fields with `ParseJson` too,
without patterns. Reject whitespace-only labels using native
`not(empty(trim(...)))` checks and the same boolean/`enum: [true]` guard.
Document-validation failures return `500 InternalError`, not `400`.
Use trimming only to test a label; never mutate request or lookup values.
Keep the response projection native so numeric fields do not pass through a
JavaScript number conversion or string interpolation.

Do not introduce `JavaScriptCode` just to implement these checks. The shared
Windows host has failed inline-code validation with
`Node worker did not start properly ('30' second timeout)` and `localhost:0`.
The native approach avoids that worker dependency. Do not change host
settings, identities, networking, or provision extra resources to work around it.

### Supported run-history protection

When `show_sample_payloads=false`, set
`runtimeConfiguration.secureData.properties` according to the action type:

| Trigger or action | Properties |
|---|---|
| Request trigger and Cosmos `ServiceProvider` reads | `["inputs", "outputs"]` |
| `ParseJson`, `Compose`, and `Response` | `["inputs"]` |

For the second row, securing inputs also hides outputs; these actions do not
support a separate Secure Outputs setting. Set the protection explicitly on
each downstream data action rather than assuming it propagates. Do not add
secure-data settings to `Scope` or `If`.

For both tracks, expose a boolean `show_sample_payloads` input defaulting to
`true` so learners can inspect the committed public samples. Apply this choice
consistently across the trigger and all data actions. With the option enabled,
omit `secureData` and omit its enclosing
`runtimeConfiguration` if that object would be empty. Null or empty
`secureData.properties` arrays fail native runtime validation with
`InvalidSecureDataConfiguration`; do not use them to disable protection.
With the option disabled, restore the table above. Authentication, identities, network
access, and authorization must remain unchanged in either mode.

In Terraform, render the conditional security blocks with `templatefile`
from `workflows/lab01-workflow/workflow.json.tftpl`; validate the rendered JSON,
not the template as literal JSON. Never upload unexpanded template expressions.
Bicep tooling must produce the same visible-by-default teaching behavior.
Inspect a new run to verify visibility; changing the definition does not
unhide previously secured history. Restore protection before using any real
or sensitive payload. Never log callback URLs or dump full app settings or
unrelated connection data, even in sample mode.

### Known malformed-JSON boundary

Malformed `application/json` is rejected by the HTTP trigger before a workflow
run starts. The observed response is HTTP `400` with Azure's
`{"error":{"code":"InvalidRequestContent","message":"..."}}` envelope, not
the workflow's `InvalidRequest` envelope. An empty trigger schema does not
prevent this platform-level parsing.

The contract remains unchanged: its malformed-JSON envelope requirement is
a known unmet limitation, not a passing workflow test. Report it explicitly.
Correctly formed JSON with missing, invalid, or extra fields must still reach
the workflow's contracted `400` response. Do not change the test's content type,
weaken validation, or add a gateway to hide the limitation.

## Workflow artifacts and connection

Deploy Standard artifacts through the site's `deployWorkflowArtifacts`
operation. The files map contains `lab01-workflow/workflow.json`; preserve every
other workflow. Do not `PUT` to `Microsoft.Web/sites/workflows`.

When migrating an existing `region-lookup`, upload and verify `lab01-workflow`
first. Retire only the old workflow's artifacts after learner approval and
successful tests of the new endpoint. Do not assume Terraform action-state
updates remove the old files. Warn that the old callback stops working and
its run history may no longer be accessible through that workflow.

The seed script creates this `serviceProviderConnections` entry in the shared
`connections.json`:

```json
{
  "lab01Cosmos": {
    "displayName": "Lab 1 region lookup",
    "parameterSetName": "ManagedServiceIdentity",
    "parameterValues": {
      "accountURI": "@appsetting('AzureCosmosDB_accountEndpoint')",
      "authProvider": {
        "Type": "ManagedServiceIdentity"
      }
    },
    "serviceProvider": {
      "id": "/serviceProviders/AzureCosmosDB"
    }
  }
}
```

### Cosmos authentication checks

Before deploying artifacts in either track, verify these exact paths in
`serviceProviderConnections.lab01Cosmos`:

| Path | Required value |
|---|---|
| `parameterSetName` | `ManagedServiceIdentity` |
| `parameterValues.accountURI` | `@appsetting('AzureCosmosDB_accountEndpoint')` |
| `parameterValues.authProvider.Type` | `ManagedServiceIdentity` |
| `serviceProvider.id` | `/serviceProviders/AzureCosmosDB` |

Keep `authProvider` inside `parameterValues`, never at the connection's top
level. Omit `authProvider.Identity` so Cosmos uses the site's system-assigned
identity, not the host-storage user-assigned identity.

The error `The required parameter 'authProvider' is missing in AAD/MI authentication`
means this nesting must be checked first; do not change roles, enable public
access, or introduce account keys to work around it. Reuse the prepared
connection rather than generating an alternative authentication shape.

The preparation script repairs only its own older connection shape; it
rejects a different endpoint or explicitly selected identity.

Reference it using `connectionName: lab01Cosmos`. For `ReadDocument`,
`inputs.parameters` contains `databaseId`, `containerId`, `itemId`, and
`partitionKey`. Put `retryPolicy` under the action's `inputs`, not beside them.
The built-in `ReadDocument` result contains the document as a JSON string in
`content`. Parse each read's string before using the lookup values to enrich
the request. Project only the nine contracted response fields.

Do not replace the site's full settings or connection file. If an artifact
deployment needs to update connections, read the current file and merge only
the required entry. Terraform may use `azapi_resource_action` for
`deployWorkflowArtifacts`, with that reason documented; Bicep must use the
same supported artifact operation through its deployment tooling.

## Validation and cleanup

Verify Lab 0's readiness first if it has changed. Before deploying, validate
workflow/connection JSON and review the selected track's format/build/preview
or fmt/validate/plan. The preview must have no foundation writes.

### Native runtime readiness

Artifact deployment success and `Healthy` from the ARM `/sites/.../workflows`
file view do not prove that the native runtime compiled the workflow.
After deployment, query the existing site's native management endpoint:

```text
GET {logic_app_id}/hostruntime/runtime/webhooks/workflow/api/management/workflows/lab01-workflow?api-version=2025-03-01
```

Check the response's `health.state`. Use a bounded registration wait, then
require `Healthy` and confirm `Receive_Request` is registered before obtaining
its callback URL and running HTTP tests. If it remains unhealthy, inspect
`health.errorMessage` and action error codes without dumping secured payloads.
Fix the workflow definition first; do not infer an RBAC or networking fault
from a schema or inline-code compilation error.

### Behavioral verification and cleanup

Test every case in `contracts/test-cases.json`, compare the successful response
with `sample-response.json`, and inspect action statuses in a successful run
to prove both actual Cosmos reads. Offline schema checks and mocked Terraform
tests do not replace these live checks. Distinguish live-tested paths from
offline-only failure-path checks; do not claim a tested outage response unless
that path was exercised.
A different seeded name must return its own display name and physical location.
Change the support tier while keeping the region to prove the second lookup is
independent. Change the request metadata to prove it passes through unchanged.
Reject output labels supplied in the request. Check the unavailable-store
error path without weakening networking or RBAC.

Retrieve the callback URL privately for the exercise only. Never commit,
output in IaC, log, or persist it. There is no browser/CORS task in this lab.

Cleanup removes `lab01-workflow` and only its unused connection entry. Verify
artifact removal explicitly; Terraform state destruction alone may leave
uploaded files. Keep the sample documents until Lab 0 cleanup, and preserve
all other labs' artifacts and the shared foundation.
