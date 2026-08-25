# Lab 1 implementation requirements

These requirements define the implementation boundary for the CRUD integration.
Read them with [`README.md`](README.md), [`contracts/openapi.yaml`](contracts/openapi.yaml),
the repository-wide
[`implementation standards`](../../docs/implementation-standards.md), and the
[`Logic App Standard baseline`](../../docs/logic-app-standard-baseline.md).

## Resource responsibilities

Both IaC tracks must create behaviorally equivalent resources:

| Resource | Requirement |
|---|---|
| Resource group | Lab-specific tags and selected location |
| Cosmos DB account | Serverless capacity with local authentication and public network access disabled |
| Cosmos private connectivity | One `Sql` private endpoint in the private-endpoint subnet, the `privatelink.documents.azure.com` private DNS zone, a VNet link, and a private DNS zone group |
| SQL database and container | `workshop` / `items` with partition key `/id` |
| Logic App hosting | Complete private Logic App Standard baseline |
| Logic App site | One Standard site with dual identities and VNet route-all |
| Logic App workflow | One HTTP-triggered workflow implementing the OpenAPI operations |
| Cosmos RBAC | System-assigned Logic App identity can read and write data only at the required scope |
| Static Web App | Free SKU hosting the starter UI |
| Application Insights | Request and workflow observability |

The user-assigned identity accesses only Logic App host storage. The
system-assigned identity accesses Cosmos DB. Do not use Cosmos account keys.

## Implementation sequence

Keep infrastructure provisioning separate from workflow behavior in both IaC
tracks:

1. Deploy the complete backend infrastructure foundation: resource group,
   private Logic App Standard hosting baseline, empty Standard site with both
   identities, Application Insights, Cosmos account, database, container, and
   least-privilege Cosmos RBAC. Disable Cosmos public network access and add its
   `Sql` private endpoint and private DNS path in this phase so the
   VNet-integrated workflow has a working data-plane route. Do not add a
   workflow definition, Static Web App, or API Management resources in this
   phase.
2. Add only the HTTP-triggered CRUD workflow and the configuration it needs to
   use the existing Cosmos container through the site's system-assigned
   identity. Do not recreate or replace foundation resources.
3. Add the Static Web App and restrict workflow CORS to its deployed origin.

The API Management modes below remain available when API Management is
explicitly requested; they are not part of the three-phase direct browser path.

## API Management modes

Model API Management as `none`, `new`, or `existing`, defaulting to `none`.

- `none`: create no API Management resources.
- `new`: create an API Management instance only when explicitly selected.
- `existing`: require its name and resource group, reference the instance in the
  current subscription, and add only the workshop API, operations, and
  API-scoped policies.

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
