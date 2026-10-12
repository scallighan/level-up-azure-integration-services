---
title: Workshop home
description: Build secure Azure integration solutions with GitHub Copilot, Bicep, and Terraform.
permalink: /
---

# Agentic Azure Integration Services Development

Build and operate Azure integration solutions while practicing a
contract-first, evidence-driven workflow with GitHub Copilot.

<div class="workshop-actions">
  <a class="button button-primary" href="{{ '/labs/00-foundation/' | relative_url }}">Start with Lab 0</a>
  <a class="button" href="{{ '/docs/copilot-working-agreement.html' | relative_url }}">Learn the Copilot loop</a>
</div>

## Workshop path

<div class="workshop-grid">
  <article class="workshop-card">
    <span class="step-number">0</span>
    <h3>Lab 0: deploy the shared foundation</h3>
    <p>Choose Bicep or Terraform and a new or existing resource group. Deploy shared Logic App hosting, private Cosmos DB, Service Bus, and monitoring.</p>
    <a href="{{ '/labs/00-foundation/' | relative_url }}">Open Lab 0</a>
  </article>
  <article class="workshop-card">
    <span class="step-number">1</span>
    <h3>Lab 1: build a CRUD integration</h3>
    <p>Add a website and CRUD workflow using Lab 0's Logic App, private Cosmos DB, and monitoring.</p>
    <a href="{{ '/labs/01-crud-integration/' | relative_url }}">Open Lab 1</a>
  </article>
  <article class="workshop-card">
    <span class="step-number">2</span>
    <h3>Lab 2: build event fan-out</h3>
    <p>Add a topic, subscriptions, and three workflows to Lab 0's Service Bus namespace and Logic App.</p>
    <a href="{{ '/labs/02-topic-fanout/' | relative_url }}">Open Lab 2</a>
  </article>
  <article class="workshop-card">
    <span class="step-number">3</span>
    <h3>Lab 3: optional workbook capstone</h3>
    <p>Approve a design from workbook evidence, then implement it using the shared foundation.</p>
    <a href="{{ '/labs/03-workbook-to-solution/' | relative_url }}">Open Lab 3</a>
  </article>
</div>

## Choose an infrastructure track

Lab 0 provides complete, ready-to-deploy code in both tracks. Later labs use
the starter prompts below to add their integrations to that shared foundation.
Both tracks create behaviorally equivalent Azure resources. Select one for the
workshop and use the cross-track review to compare resource responsibilities,
identity boundaries, and runtime behavior.

| Track | Lab 0 deployment code | Lab 1 prompt | Lab 2 prompt | Lab 3 prompt |
|---|---|---|---|---|
| Bicep | [Foundation Bicep](labs/00-foundation/iac/bicep/main.bicep) | [CRUD Bicep prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/01-crud-bicep.prompt.md) | [Fan-out Bicep prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-bicep.prompt.md) | [Workbook Bicep prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/03-workbook-bicep.prompt.md) |
| Terraform | [Foundation Terraform](labs/00-foundation/iac/terraform/main.tf) | [CRUD Terraform prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/01-crud-terraform.prompt.md) | [Fan-out Terraform prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-terraform.prompt.md) | [Workbook Terraform prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/03-workbook-terraform.prompt.md) |

> **Cost notice:** The labs create billable resources, including Windows WS1
> Workflow Standard plans and private endpoints. Use a non-production
> subscription. Cleanup is optional between labs when continuing with reused
> resources; complete it when finished with the workshop, removing dependent
> resources before their shared foundation.

## Facilitator resources

- [Instructor guide](docs/instructor-guide.md)
- [Coaches guide](docs/coaches-guide.md)
- [Logic App Standard infrastructure baseline](docs/logic-app-standard-baseline.md)
