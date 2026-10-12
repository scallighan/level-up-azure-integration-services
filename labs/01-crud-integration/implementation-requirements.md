# Lab 1 implementation requirements

These requirements define the implementation boundary for the CRUD integration.
Read them with [`README.md`](README.md), [`contracts/openapi.yaml`](contracts/openapi.yaml),
the repository-wide
[`implementation standards`](../../docs/implementation-standards.md), and the
[`Logic App Standard baseline`](../../docs/logic-app-standard-baseline.md).

## Resource responsibilities

Complete [Lab 0](../00-foundation/README.md) first. Both tracks must reference
its explicit non-secret handoff rather than create or own a second foundation:

| Resource | Requirement |
|---|---|
| Resource group | Reference Lab 0's parent without managing it; tag new frontend/extension resources `lab=01` |
| Cosmos DB account | Reference Lab 0's private, serverless, Entra-only account |
| Cosmos private connectivity | Verify Lab 0's `Sql` endpoint, private DNS zone, link, and zone group |
| SQL database and container | Reference Lab 0's `workshop` / `items`, partition key `/id` |
| Logic App hosting | Reference the complete Lab 0 private Standard baseline |
| Logic App site | Reference Lab 0's dual-identity Standard site; never import or manage the parent |
| Logic App workflow | One HTTP-triggered workflow implementing the OpenAPI operations |
| Cosmos RBAC | Verify Lab 0's existing container-scoped system-identity grant; do not duplicate it |
| Static Web App | Free SKU hosting the starter UI |
| Application Insights | Use Lab 0's wired request and workflow observability |

The user-assigned identity accesses only Logic App host storage. The
system-assigned identity accesses Cosmos DB. Do not use Cosmos account keys.

## Implementation sequence

Keep infrastructure provisioning separate from workflow behavior in both IaC
tracks:

1. Verify Lab 0 with `scripts/verify-foundation.sh` and configure explicit
   existing-resource references from `foundation.deployment.json`. Create no
   backend foundation resources and make no foundation writes.
2. Add only the HTTP-triggered CRUD workflow and the configuration it needs to
   use the existing Cosmos container through the site's system-assigned
   identity. Do not recreate or replace foundation resources.
3. Add the Static Web App and restrict workflow CORS to its deployed origin.

Preserve other labs' workflow artifacts and app-level connections. Merge only
Lab 1's required connection entry; never replace the shared site's complete
settings or erase other workflows. Keep `lab=00` tags and Lab 0 ownership.
Cleanup removes only Lab 1-owned resources, the CRUD workflow, and its unused
connection entry. Terraform action-state destruction alone may not delete
uploaded artifacts; verify their removal explicitly. Never delete the Lab 0
parent resource group or foundation.

The API Management modes below remain available when API Management is
explicitly requested; they are not part of the three-phase direct browser path.

## API Management modes

Model API Management as `none`, `new`, or `existing`, defaulting to `none`.

- `none`: create no API Management resources.
- `new`: create an API Management instance only when explicitly selected.
- `existing`: require its name and resource group, reference the instance in the
  current subscription, and add only the workshop API, operations, and
  API-scoped policies.

Treat the selected mode as a stable, lab-wide input. Preserve it across tasks
unless the learner explicitly requests a mode change. When the mode is `none`,
later tasks must continue to create no API Management resources.

Reject inconsistent mode-specific inputs. Never change service-wide settings on
an existing API Management instance.

## API and workflow behavior

- Treat [`contracts/openapi.yaml`](contracts/openapi.yaml) as the source of truth
  for operations, request bodies, responses, and status codes.
- Use `/id` as the Cosmos container partition key.
- Route the starter app's canonical request by OpenAPI `operationId`.
- Return deliberate validation, conflict, not-found, and unexpected-error
  responses that match the contract.
- Make write retry behavior safe and explicit.
- Handle CORS preflight and allow only the deployed Static Web App origin.

## Known-good Standard workflow and Cosmos shape

Use these tested requirements instead of inventing a connector or artifact
deployment shape:

- Deploy Standard workflow artifacts through the App Service
  `deployWorkflowArtifacts` operation. The files map contains the app-level
  `connections.json` and `<workflow-name>/workflow.json`. Do not create the
  workflow by sending `PUT` to `Microsoft.Web/sites/workflows`; that endpoint
  returns `405 Method Not Allowed` for this deployment shape.
- For Terraform, use an `azapi_resource_action` against the existing
  `Microsoft.Web/sites` resource with action `deployWorkflowArtifacts` and
  method `POST`. Keep the reason for AzAPI documented.
- Configure the built-in `/serviceProviders/AzureCosmosDB` connection with
  `parameterSetName` set to `ManagedServiceIdentity`,
  `parameterValues.accountURI` set to the non-secret Cosmos endpoint app
  setting, and `authProvider.Type` set to `ManagedServiceIdentity`. Do not use
  `accountEndpoint` as the connector parameter name and do not select the
  host-storage user-assigned identity.
- Put a ServiceProvider action's `retryPolicy` inside `inputs`. Fixed retry
  intervals must be at least `PT5S`.
- Read connector failures from `actions('<action-name>').code`. The tested
  codes used by this workflow are `Conflict` and `NotFound`; do not expect an
  HTTP-style `outputs.statusCode`.
- Use `CreateOrUpdateDocument` with `isUpsert=false` for create. For update,
  first use `ReadDocument` to preserve the contracted `404`, then use
  `CreateOrUpdateDocument` with the path ID copied into the document and
  `isUpsert=true`. The required update path does not use `PatchItem`.
- Disable automatic retries for create, update, and delete writes. Bounded
  read/query retries may use two fixed retries at `PT5S`.
- Project only `id`, `name`, and `status` from Cosmos results. Never return
  `_rid`, `_self`, `_etag`, `_attachments`, `_ts`, connector diagnostics, or
  full failure output.

Before deploying the workflow, verify that the Cosmos private endpoint
connection is approved, the private DNS zone has an A record, and the VNet link
is provisioned. A successful Terraform or Bicep deployment does not prove the
workflow can resolve or reach Cosmos.

The direct browser path uses a temporary Logic App callback URL for this
exercise. Never commit, output, log, or persist it in browser storage. Retrieve
it only for the active exercise and delete the workflow during cleanup.
