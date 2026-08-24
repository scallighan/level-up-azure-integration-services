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
| Cosmos DB account | Serverless capacity with local authentication disabled |
| SQL database and container | `workshop` / `items` with partition key `/id` |
| Logic App hosting | Complete private Logic App Standard baseline |
| Logic App | One Standard site with dual identities, VNet route-all, and an HTTP request trigger |
| Cosmos RBAC | System-assigned Logic App identity can read and write data only at the required scope |
| Static Web App | Free SKU hosting the starter UI |
| Application Insights | Request and workflow observability |

The user-assigned identity accesses only Logic App host storage. The
system-assigned identity accesses Cosmos DB. Do not use Cosmos account keys.

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

The direct browser path uses a temporary Logic App callback URL for this
exercise. Never commit, output, log, or persist it in browser storage. Retrieve
it only for the active exercise and delete the workflow during cleanup.
