---
title: "Lab 1: Lookup and transform"
permalink: /labs/01-crud-integration/
---

# Lab 1: Lookup and transform

Use Cosmos DB to enrich a JSON deployment request. Keep the request details
unchanged, and add region details and support-tier details from two lookups.
The workflow transforms JSON only; it does not deploy Azure resources.

**Time:** 60 minutes. **Required:** [Lab 0](../00-foundation/README.md),
Python 3, and the same Azure CLI session.

![HTTP request to Logic App to private Cosmos DB and a transformed JSON response](../../docs/assets/lab-01-lookup-architecture.svg)

This lab uses public data from Microsoft's
[Azure regions list](https://learn.microsoft.com/en-us/azure/reliability/regions-list?tabs=all).
The support tiers are fictional teaching data, not Azure support plans.
It needs no website or API Management.

## Task 1: prepare the lookup data and connection

From the repository root, run:

```bash
python3 scripts/prepare-lab1.py foundation.deployment.json
```

The script loads [six sample regions](contracts/regions.json) and
[three synthetic support tiers](contracts/support-tiers.json) into Lab 0's
`workshop/items` container. It runs a temporary helper workflow inside the
existing site so Cosmos DB stays private. It removes the helper afterward
and leaves the `lab01Cosmos` connection ready for your workflow.
Rerunning the script updates the same nine records. If you seeded an earlier
version of this lab, run it again to add the support-tier records.

To keep the helper and its run history for debugging, use:

```bash
python3 scripts/prepare-lab1.py foundation.deployment.json --keep-workflow
```

The script prints the retained workflow's name and disables it to prevent
scheduled runs. Open it under the site's **Workflows** in the Azure portal.
Disabling it updates an app setting and may restart the shared site.
Enable it temporarily if you need to rerun it, then disable it again.
When finished, delete that helper and its `Workflows.<name>.FlowState` app
setting. Normal runs without the flag still remove their helper.

## Task 2: generate the workflow

Give Copilot this prompt. Keep the Bicep or Terraform track you chose in Lab 0.

```text
Build the region-lookup HTTP workflow for Lab 1. Follow
labs/01-crud-integration/implementation-requirements.md and its OpenAPI contract.
Use programmaticName and supportTier for two independent Cosmos DB lookups.
Preserve all five request fields. Add regionDisplayName, physicalLocation,
supportTierDisplayName, and numeric responseTimeHours from the lookup records.
Reuse Lab 0 and lab01Cosmos; do not hardcode values. Show the files and checks
before deploying.
```

Review the generated workflow and deployment artifacts. Approve deployment
only to the existing Lab 0 site; there should be no foundation changes.
The [implementation requirements](implementation-requirements.md) contain
the connection, lookup, and error-handling details.

## Task 3: send a request

In the Azure portal, open `region-lookup` and copy its HTTP trigger callback
URL. Paste it into the hidden prompt below. Do not save it in a file or commit it.

```bash
read -r -s -p "Workflow callback URL: " WORKFLOW_URL
printf '\n'
curl --silent --show-error --fail-with-body \
  --header 'Content-Type: application/json' \
  --data @labs/01-crud-integration/contracts/sample-request.json \
  "$WORKFLOW_URL"
unset WORKFLOW_URL
```

Request:

```json
{
  "requestId": "REQ-1042",
  "workloadName": "inventory-api",
  "instanceCount": 2,
  "programmaticName": "westus",
  "supportTier": "standard"
}
```

Expected HTTP `200` response:

```json
{
  "requestId": "REQ-1042",
  "workloadName": "inventory-api",
  "instanceCount": 2,
  "programmaticName": "westus",
  "supportTier": "standard",
  "regionDisplayName": "West US",
  "physicalLocation": "California",
  "supportTierDisplayName": "Standard",
  "responseTimeHours": 8
}
```

What changed:

| Fields | Rule |
|---|---|
| All five request fields | Copy unchanged, including the numeric instance count |
| `regionDisplayName` | Add the region document's `displayName` |
| `physicalLocation` | Add the region document's `physicalLocation` |
| `supportTierDisplayName` | Add the support document's `displayName` |
| `responseTimeHours` | Add the support document's integer response time |

The request contains lookup keys, not placeholder output fields. `supportTier`
is independent of the region: the same region can use any seeded support tier.

## Task 4: check lookup and error behavior

Use the [test cases](contracts/test-cases.json) to check:

| Request | Expected result |
|---|---|
| `westus` + `standard` | `200`, adds `West US`, `California`, `Standard`, and `8` hours |
| `westeurope` + `standard` | `200`, changes only the region lookup details |
| `westus` + `priority` | `200`, changes only the support lookup details to `Priority` and `1` hour |
| Different request ID, workload name, or instance count | Preserve the supplied values and types |
| Output fields included in the request | `400`, unexpected fields |
| `notaregion` | `404`, `RegionNotFound` |
| Unknown support tier | `404`, `SupportTierNotFound` |
| Missing required field or wrong field type | `400`, invalid request |

Only the six seeded regions and three seeded support tiers are available.
A valid Azure region that is not seeded also returns `404`. Confirm both
lookups read Cosmos DB rather than using a hardcoded map, and return no Cosmos
system fields. Neither lookup may fail silently or return a partial response.

## Cleanup

Remove only the `region-lookup` workflow and the `lab01Cosmos` connection entry
if nothing else uses it. Preserve other workflows, connections, and all Lab 0
resources. The nine sample documents can remain until Lab 0 cleanup.
