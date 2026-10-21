---
title: "Lab 0: Shared Azure foundation"
permalink: /labs/00-foundation/
---

# Lab 0: Shared Azure foundation

Deploy the shared infrastructure once: Logic App Standard with private host
storage, private Cosmos DB, Service Bus Standard, and Application Insights.
Later labs add integrations without recreating this foundation.

**Time:** 30-45 minutes plus Azure provisioning.

## Before you start

Use Bash, Azure CLI, jq, and either Bicep (`az bicep install`) or Terraform
**1.14.4**. Choose a non-production subscription with deployment and
role-assignment permissions. No GitHub login or Copilot session is required.

Read the [implementation requirements](implementation-requirements.md) and
[hosting baseline](../../docs/logic-app-standard-baseline.md).
WS1, private endpoints, storage, Cosmos, Service Bus, and monitoring are billable.

## 1. Set up

From the repository root, choose one track:

### Bicep

```bash
./scripts/foundation.sh setup bicep
```

### Terraform

```bash
./scripts/foundation.sh setup terraform
```

Enter your subscription, prefix, region, and optional existing resource group.
A blank group creates a workshop group; an existing group remains yours.
Setup resolves your current `az login` user's object ID and asks you to confirm
namespace-wide Service Bus publishing access. It saves that selection in `.env`,
checks tools/access/quota, and registers providers. Application and managed
identity logins are not accepted for student selection.

## 2. Preview

### Bicep

```bash
./scripts/foundation.sh preview bicep
```

### Terraform

```bash
./scripts/foundation.sh preview terraform
```

Review the changes before deploying. Only the foundation may be created;
existing group metadata and unrelated resources must remain untouched.
The selected user receives **Azure Service Bus Data Sender** on the workshop
namespace, covering all its topics and queues. Neither Logic App identity
receives sender access. This is a workshop convenience; production publishers
should use narrower entity-scoped grants.

## 3. Deploy

### Bicep

```bash
./scripts/foundation.sh deploy bicep
```

### Terraform

```bash
./scripts/foundation.sh deploy terraform
```

Keep the same track and inputs throughout the workshop. The helper saves
`foundation.deployment.json`; copy its `resource_group_name` into
`FOUNDATION_RESOURCE_GROUP_NAME` in `.env`. Keep both files local.
The handoff also records `publisher_principal_id`. Role propagation can take
several minutes before publishing works.

For an existing foundation without the publisher grant, repeat setup, preview,
and deployment using the **same track, subscription, prefix, region, and group**.
Review the preview: the intended addition is the user sender grant, not a second
foundation. Setup alone does not create role assignments.

## 4. Check

```bash
bash scripts/verify-foundation.sh foundation.deployment.json
```

Continue when readiness passes and the empty site and handoff are available.
[Lab 1](../01-crud-integration/README.md) and [Lab 2](../02-topic-fanout/README.md)
can then be completed independently.

## Cleanup

Keep the foundation until all labs are finished. Remove later-lab resources
first, then follow the [cleanup instructions](implementation-requirements.md#cleanup).
Never delete an existing parent resource group.
