---
title: "Lab 1: CRUD integration"
permalink: /labs/01-crud-integration/
---

# Lab 1: CRUD integration

Connect a small item-management website to an HTTP-triggered Logic App and
Cosmos DB.

**Time:** 90 minutes. **Required:** [Lab 0](../00-foundation/README.md).

![Browser to Static Web Apps to Logic App to private Cosmos DB](../../docs/assets/lab-01-crud-architecture.svg)

## Start

Read the [implementation requirements](implementation-requirements.md) and
[OpenAPI contract](contracts/openapi.yaml).
Initialize one track with the
[Bicep starter](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/01-crud-bicep.prompt.md)
or [Terraform starter](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/01-crud-terraform.prompt.md)
([how to invoke](../../docs/copilot-working-agreement.md#invoking-workshop-prompt-files)).
The starter creates files only; use the task prompts below one at a time.

Reuse Lab 0's `.env` and `foundation.deployment.json`. Set
`FOUNDATION_RESOURCE_GROUP_NAME` from the handoff and keep
`API_MANAGEMENT_MODE=none` for this direct browser exercise.

```bash
set -a; source .env; set +a
```

For each change, have Copilot explain the resource graph, identities, files,
and checks before approval. Run Bicep format/build/what-if or Terraform
fmt/validate/plan; review the preview and artifact files before deploying.

## Task 1: reference the foundation

```text
Verify foundation.deployment.json against Azure and configure existing-resource
references in my selected track. Follow the Lab 1 implementation requirements.
Do not create, import, or modify any Lab 0 resource or implement later tasks.
```

Run `bash scripts/verify-foundation.sh foundation.deployment.json`.
The references must resolve with no managed-resource changes.

## Task 2: add the CRUD workflow

```text
Add only the HTTP-triggered CRUD workflow to the existing site. Route the
starter app's operationId requests using the OpenAPI contract and access
workshop/items with the site's system identity. Follow the tested artifact,
connection, retry, and response requirements. Preserve other labs' artifacts.
```

Check create, list, get, update, and delete against the contract before adding
the frontend. Do not change hosting, Cosmos, or existing RBAC.

## Task 3: connect the frontend

```text
Add the Free-tier Static Web App for app/ and restrict workflow CORS, including
preflight, to its deployed origin. Keep the direct Logic App path; do not add
API Management or retrieve, output, log, or persist the callback URL.
```

Deploy `app/`. Retrieve the callback URL privately in the Azure portal, select
**Direct Logic App** in the UI, and paste it for this session only.
Never commit it or save it in browser storage.

## Task 4: test end to end

Create, list, get, update, and delete an item in the browser. Check contracted
status codes and bodies, validation/conflict/not-found responses, and the same
correlation ID in telemetry. Responses must not expose Cosmos system fields.

## Cleanup

Remove only Lab 1's frontend, `items-crud` workflow, and unused connection
entry. Verify uploaded artifacts are removed; Terraform destroy alone may
leave them behind. Preserve Lab 0 and other labs' resources
([ownership details](implementation-requirements.md#implementation-sequence)).
