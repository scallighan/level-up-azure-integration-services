---
title: Workshop home
description: Build secure Azure integration solutions with GitHub Copilot, Bicep, and Terraform.
permalink: /
---

# Agentic Azure Integration Services Development

Build and operate Azure integration solutions while practicing a
contract-first, evidence-driven workflow with GitHub Copilot.

<div class="workshop-actions">
  <a class="button button-primary" href="{{ '/docs/prerequisites.html' | relative_url }}">Start with prerequisites</a>
  <a class="button" href="{{ '/labs/01-crud-integration/' | relative_url }}">Begin Lab 1</a>
</div>

## Workshop path

<div class="workshop-grid">
  <article class="workshop-card">
    <span class="step-number">1</span>
    <h3>Prepare</h3>
    <p>Verify Azure access, GitHub Copilot, and the Bicep or Terraform toolchain.</p>
    <a href="{{ '/docs/prerequisites.html' | relative_url }}">Review prerequisites</a>
  </article>
  <article class="workshop-card">
    <span class="step-number">2</span>
    <h3>Learn the loop</h3>
    <p>Give Copilot bounded context, inspect its changes, preview deployments, and test contracts.</p>
    <a href="{{ '/docs/copilot-working-agreement.html' | relative_url }}">Read the working agreement</a>
  </article>
  <article class="workshop-card">
    <span class="step-number">3</span>
    <h3>Build a CRUD integration</h3>
    <p>Connect a website, Logic App Standard, Cosmos DB, and optional API Management.</p>
    <a href="{{ '/labs/01-crud-integration/' | relative_url }}">Open Lab 1</a>
  </article>
  <article class="workshop-card">
    <span class="step-number">4</span>
    <h3>Build event fan-out</h3>
    <p>Route one Service Bus event to three independently routed workflows.</p>
    <a href="{{ '/labs/02-topic-fanout/' | relative_url }}">Open Lab 2</a>
  </article>
  <article class="workshop-card">
    <span class="step-number">5</span>
    <h3>Optional capstone: design from a workbook</h3>
    <p>Turn payload and transformation evidence into an approved design, then implement it.</p>
    <a href="{{ '/labs/03-workbook-to-solution/' | relative_url }}">Open Lab 3</a>
  </article>
</div>

## Choose an infrastructure track

Both tracks create behaviorally equivalent Azure resources. Select one for the
workshop and use the cross-track review to compare resource responsibilities,
identity boundaries, and runtime behavior.

| Track | Lab 1 prompt | Lab 2 prompt | Lab 3 prompt |
|---|---|---|---|
| Bicep | [CRUD Bicep prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/01-crud-bicep.prompt.md) | [Fan-out Bicep prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-bicep.prompt.md) | [Workbook Bicep prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/03-workbook-bicep.prompt.md) |
| Terraform | [CRUD Terraform prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/01-crud-terraform.prompt.md) | [Fan-out Terraform prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-terraform.prompt.md) | [Workbook Terraform prompt](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/03-workbook-terraform.prompt.md) |

> **Cost notice:** The labs create billable resources, including Windows WS1
> Workflow Standard plans and private endpoints. Use a non-production
> subscription and complete each lab's cleanup task.

## Facilitator resources

- [Instructor guide](docs/instructor-guide.md)
- [Coaches guide](docs/coaches-guide.md)
- [Logic App Standard infrastructure baseline](docs/logic-app-standard-baseline.md)
