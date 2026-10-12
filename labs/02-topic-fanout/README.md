---
title: "Lab 2: Service Bus topic fan-out"
permalink: /labs/02-topic-fanout/
---

# Lab 2: Service Bus topic fan-out

Publish one `order.created` event to an Azure Service Bus topic and process an
independent copy in three workflows: audit, fulfillment, and notification.

**Time:** 75 minutes

**Required:** complete [Lab 0](../00-foundation/README.md). Lab 1 is not required.
Reuse Lab 0's site, Service Bus namespace, and monitoring through the local
`foundation.deployment.json` handoff.

## Learning objectives

- Ground Copilot in an event schema and example rather than prose alone.
- Provision equivalent Service Bus and Logic App resources with Bicep or
  Terraform.
- Use topic subscriptions for independent delivery and failure isolation.
- Review generated workflows for locks, retries, completion, and dead lettering.
- Observe one correlation ID across multiple workflow runs.

## Architecture

![Lab 2 architecture showing Service Bus topic fan-out to three workflows in one Logic App Standard site](../../docs/assets/lab-02-topic-fanout-architecture.svg)

Each workflow receives from exactly one subscription. A failure in notification
must not remove the audit or fulfillment copies.

All three workflows run in one private-networked Logic App Standard site on the
hosting foundation defined in
[`docs/logic-app-standard-baseline.md`](../../docs/logic-app-standard-baseline.md).
Lab 2 references the foundation, site, and namespace already deployed by
Lab 0. The site's system identity receives access
at each subscription scope, never at namespace scope. The host-storage identity
remains limited to host storage.

## Event contract

Use:

- [`contracts/order-created.schema.json`](contracts/order-created.schema.json)
- [`contracts/sample-order-created.json`](contracts/sample-order-created.json)

Publish these Service Bus application properties with the sample:

| Property | Value |
|---|---|
| `eventType` | `order.created` |
| `schemaVersion` | `1.0` |
| `correlationId` | Same value as the JSON body |

## Implementation reference

Read [`implementation-requirements.md`](implementation-requirements.md) before
starting. It defines the broker topology, shared Logic App hosting foundation,
identity boundaries, and message settlement behavior for both IaC tracks. The
task prompts below intentionally describe outcomes rather than repeat those
guardrails.

## Choose a track

- **Bicep:** invoke
  [`.github/prompts/02-fanout-bicep.prompt.md`](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-bicep.prompt.md)
  and work in `labs/02-topic-fanout/iac/bicep/`.
- **Terraform:** invoke
  [`.github/prompts/02-fanout-terraform.prompt.md`](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-terraform.prompt.md)
  and work in `labs/02-topic-fanout/iac/terraform/`.

Invoke the selected prompt once from the repository root. It creates only the
initial file structure, minimal base files, and a path-local `AGENTS.md` with
the track's mandatory references and guardrails. It does not implement Step 0
or infer what to build next. Review the starter files, then use the bounded
prompt under Step 0.

Reuse the ignored root `.env` from Lab 0 for stable, non-secret deployment
inputs. Keep `FOUNDATION_RESOURCE_GROUP_NAME` set from the handoff.
Source `.env` once per terminal; Terraform should consume exported `TF_VAR_*`
values instead of repeated `-var` arguments, while Bicep commands should
reference the exported shell values. Never store connection strings, access
keys, or observability credentials in `.env`.

## Step 0: verify the Lab 0 shared foundation

**Outcome:** reference Lab 0's private Logic App Standard site, namespace, and
observability before creating Lab 2 integration resources.

There is no standalone `new` hosting mode. If Lab 0 was skipped or cleaned up,
complete it first. Lab 2 owns messaging children, roles, and workflow artifacts,
not the shared namespace, site, or parent resource group.

**Prompt Copilot**

```text
Read foundation.deployment.json and verify the Lab 0 resources against Azure.
Prepare explicit existing-resource references in my selected IaC track for the
integration subnet, host storage, host identity, WS1 plan, observability,
Standard site, and Standard Service Bus namespace. Require
FOUNDATION_RESOURCE_GROUP_NAME. Use Bicep existing resources or Terraform
data sources/explicit IDs, not imports or managed foundation resource blocks.

Do not create a resource group or hosting foundation, modify the namespace or
parent site, or add messaging entities, receiver RBAC, connections, or workflows.

Before editing, explain the existing resource graph, required handoff inputs,
compatibility checks, ownership and cleanup boundaries, cost-bearing resources,
non-secret outputs, expected files, and validation commands. Wait for my
approval.
```

**Review before approving:** reject missing or incompatible references. Do not
import, retag, modify, replace, or delete Lab 0's resources. Lab 2 may later own
child workflows and subscription-scoped roles. No credential or monitoring
connection string may be an output.

**Validate:** run `bash scripts/verify-foundation.sh foundation.deployment.json`.
Format/build or fmt/validate/plan the configured references. This phase must
contain no managed-resource changes.

**Done when:** the references resolve and Lab 2 cannot delete the shared
foundation or parent group.

## Task 1: deploy the integration infrastructure

**Outcome:** create the broker topology and authorize the selected Logic App
site without adding receiver workflow definitions.

**Prompt Copilot**

```text
Using the selected shared hosting foundation, create the Lab 2 integration
infrastructure in my selected IaC track. Reference Lab 0's Standard Service Bus
namespace and add the orders topic, audit, fulfillment, and notification subscriptions
and rules; managed-identity connection configuration for the selected Logic App
site; three receiver role assignments for its system identity, each scoped to
one subscription; and correlated observability using Lab 0 monitoring.
Preserve other labs' workflows and merge the app-level connection entries
without replacing them. Do not change parent-site settings or ownership.

Do not add audit, fulfillment, or notification workflow definitions.

Before editing, provide a routing diagram or table and explain the SKU,
default-rule removal, SQL filters, duplicate detection, lock duration, maximum
delivery count, message TTL, the site and workflow resource graph, the shared
system-identity tradeoff, RBAC scopes, expected files, non-secret outputs, and
validation commands.
Wait for my approval.
```

**Review before approving:** confirm that Standard SKU supports the requested
features, duplicate detection uses `MessageId`, each `$Default` rule is removed,
all delivery settings are deliberate, the site identity receives only at the
three subscription scopes rather than namespace scope, and no workflow
definition or connection string is present.

**Validate and deploy:** use a resource-group-scoped Bicep entry point because
Lab 2 does not create a group. Terraform consumes `TF_VAR_foundation_resource_group_name`.

```bash
# Bicep
az bicep format --file labs/02-topic-fanout/iac/bicep/main.bicep
az bicep build --file labs/02-topic-fanout/iac/bicep/main.bicep --stdout >/dev/null
az deployment group what-if \
  --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$FOUNDATION_RESOURCE_GROUP_NAME" \
  --template-file labs/02-topic-fanout/iac/bicep/main.bicep \
  --parameters prefix="$WORKSHOP_PREFIX" location="$AZURE_LOCATION"
# After reviewing the preview:
az deployment group create \
  --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$FOUNDATION_RESOURCE_GROUP_NAME" --name "fanout-$WORKSHOP_PREFIX" \
  --template-file labs/02-topic-fanout/iac/bicep/main.bicep \
  --parameters prefix="$WORKSHOP_PREFIX" location="$AZURE_LOCATION"

# Terraform
terraform -chdir=labs/02-topic-fanout/iac/terraform init
terraform -chdir=labs/02-topic-fanout/iac/terraform fmt -check
terraform -chdir=labs/02-topic-fanout/iac/terraform validate
terraform -chdir=labs/02-topic-fanout/iac/terraform plan
# After reviewing the preview:
terraform -chdir=labs/02-topic-fanout/iac/terraform apply
```

Previews must show only messaging children, scoped grants, and lab artifacts,
not namespace/site/foundation updates. Inspect workflow artifact file maps too;
ARM what-if may not show file-level changes for deployment actions.

**Done when:** Service Bus Explorer shows the topic, exactly three
subscriptions, and the intended rule on each; Azure shows three
subscription-scoped receiver assignments for the selected site identity.

## Task 2: implement isolated workflow receivers

**Outcome:** add only the three independently deployable receiver workflows to
the selected Logic App Standard site.

**Prompt Copilot**

```text
Add audit, fulfillment, and notification as three independently deployable
workflows in the selected Logic App Standard site. Each workflow must use the
site's managed-identity connection and receive from exactly one assigned
Service Bus subscription.

Do not create or replace the shared hosting foundation, Service Bus resources,
parent Logic App site, identity, RBAC, connections, or observability resources.

Before editing, explain the per-workflow resource and file changes, peek-lock
flow, processing and failure scopes, completion and dead-letter behavior,
correlation handling, and validation commands. Wait for my approval.
```

**Review before approving:** each workflow must receive from exactly one
subscription, complete only after processing succeeds, and preserve retries and
dead lettering. Keep the audit, fulfillment, and notification actions within
the lightweight core-lab boundary.

**Done when:** each workflow references only its assigned subscription and no
connection string appears in source, parameters, state output, or run history.

## Task 3: publish and trace one event

In Azure Portal, open the `orders` topic and use **Service Bus Explorer** to send
the sample JSON. Set:

- `ContentType` to `application/json`;
- `MessageId` to the sample event ID;
- `CorrelationId` to the sample correlation ID; and
- the application properties from the contract table.

Use Microsoft Entra authentication. Give the publishing student **Azure Service
Bus Data Sender at the `orders` topic scope**, not namespace-wide data access;
the site's receiver roles do not authorize the student to send. Confirm the
student's principal and explicit role-assignment permission before granting it.
Do not enable SAS authentication to make the portal test work.

**Prompt Copilot**

```text
Using the committed event schema and sample, predict the subscription message
counts and workflow runs after publishing exactly one order.created event.
Explain how MessageId, CorrelationId, eventType, and schemaVersion affect
routing, duplicate detection, and telemetry. Do not edit infrastructure.
```

Review the prediction, then send exactly one event.

**Done when:** all three workflows run once and preserve the same event ID and
correlation ID.

## Task 4: prove failure isolation

Temporarily make the notification processing scope fail before its complete
action. Send a new event with new IDs.

**Prompt Copilot**

```text
Create a controlled failure-isolation test for the notification workflow.
Describe the smallest temporary change, expected delivery-count progression,
retry and dead-letter behavior, evidence to collect from all three
subscriptions, and the exact revert. Do not weaken authentication, networking,
or message settlement.
```

Observe:

- audit and fulfillment complete their copies;
- notification retries its own copy;
- delivery count increases only on the notification subscription; and
- the message reaches that subscription's dead-letter queue after the configured
  maximum deliveries.

Revert the deliberate failure. Ask Copilot to explain how a dead-letter replay
tool should preserve `MessageId`, correlation, and diagnostic context without
creating an infinite retry loop.

**Done when:** audit and fulfillment complete independently, only notification
retries and dead-letters its copy, and the deliberate failure has been reverted.

## Cross-track review

Pair with someone using the other IaC language and invoke
[`review-iac-parity.prompt.md`](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/review-iac-parity.prompt.md).
Pay special attention to default rules, RBAC scope, lock handling, and resources
that cleanup could orphan.

## Optional cleanup

**Skip this section if you are continuing with resources that the next lab's
approved design explicitly reuses.** Otherwise, clean up when you stop or no
longer need the Lab 2 deployment. Retained resources continue to incur charges;
complete cleanup at the end of the workshop, removing dependent lab resources
first.

Never delete the Lab 0 resource group, namespace, or site. For Bicep, review
and delete only Lab 2's topic (including subscriptions/rules), role assignments,
workflow artifacts, and unused connection entry. For Terraform, review
`plan -destroy` then `destroy` for the Lab 2 track; explicitly remove its
uploaded workflows because destroying deployment-action state may not remove
artifacts. Remove the student's lab-specific sender grant as well. Preserve
Lab 1/3 artifacts and confirm Lab 0's foundation remains intact.

## Stretch goals

- Add a second event type and route it to only two subscriptions.
- Add a dead-letter monitor without automatically replaying poison messages.
- Use a session ID to preserve per-order processing order.
- Add a publisher Logic App fronted by API Management.
