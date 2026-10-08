---
title: "Lab 3: Workbook to Azure integration solution"
permalink: /labs/03-workbook-to-solution/
---

# Lab 3: Workbook to Azure integration solution

Use a local workbook to **propose an Azure design**, then **implement the
approved design** with Bicep or Terraform. External systems are mocked in this
lab.

**Time:** 90-150 minutes, depending on workbook complexity and target access

![Workbook to approved design to Azure implementation](../../docs/assets/lab-03-workbook-design-architecture.svg)

Read [`implementation-requirements.md`](implementation-requirements.md) for the
technical requirements. Keep workbooks, raw evidence, and images local; never
commit customer data or identifiers. Use sanitized fixtures and generic names
in committed designs and code.

## Workbook interpretation rules

Trim whitespace and compare names case-insensitively. Read the actual headers
and cell alignment, including merged headers, rather than fixed column letters.

| Workbook element | Design rule |
|---|---|
| `Architect Diagram` or `Architecture Diagram` tab | Flow guidance, not a workflow. Review embedded images and arrows. |
| XRef tab or table entries | Reference lookup data, not a workflow. An XRef table inside a processing tab does not exclude that tab. |
| Processing tab or table name beginning with `Source` | Starting point; include a workflow and a helper script to send sample Input to its ingress queue. |
| Every non-informational tab | One separate Logic App Standard workflow. |
| `Input` columns | Incoming-message examples used to derive sanitized fixtures and contracts. |
| `Transformation rule`, `Transformation Logic`, or `Dataweave` columns | Mapping, validation, defaults, conversions, and lookup behavior. |
| `Output` columns | Expected transformed message, published to an output topic for downstream consumption. |

Use diagram arrows and matching upstream Output/downstream Input to connect
tabs, not worksheet order. Service Bus carries every inter-tab handoff:
publish to a topic and receive through a downstream subscription, with separate
subscriptions for fan-out. Resolve missing mappings, conflicting examples, and
ambiguous tabs before approval.

## Task 1: propose and approve the Azure design

**Outcome:** a reviewed design based on your workbook and the rules above.

Reference your local workbook in this prompt, replacing `sample.xlsx` with its
path:

```text
Read the Lab 3 README, implementation requirements, repository implementation
standards, and Lab 3 contracts.

Use sample.xlsx locally. Run scripts/extract-integration-workbook.py to extract
all sheets into /tmp/workbook-evidence.md, and review embedded images separately.
Apply the workbook interpretation rules to propose the smallest secure Azure
Integration Services design. Include one workflow per processing tab, Source
helpers, XRef lookup artifacts, Service Bus handoffs, and mocked external systems.

Summarize the flow and resource graph, identity boundaries, costs, and cleanup
ownership. Cite workbook evidence locally; separate facts from assumptions and
list conflicts or missing information that need my decision.

Write labs/03-workbook-to-solution/design/integration-design.json using generic
names and sanitized evidence. Validate it against the Lab 3 design schema.
Keep status proposed. Do not initialize IaC, implement, or deploy resources.
```

The [sample design](contracts/sample-simple-design.json) illustrates the contract
structure, not a solution to copy; its names and cell references are illustrative.
Review the proposal, resolve all assumptions marked
`mustConfirmBeforeImplementation`, and change `status` to `approved`.

**Done when:** the design is schema-valid, the flows and resource graph are
understood, and you have approved it.

## Task 2: implement the approved design

**Outcome:** the approved Azure solution working end to end against mocks.

Choose one starter prompt to initialize your IaC track:

- **Bicep:** [Lab 3 Bicep starter](../../.github/prompts/03-workbook-bicep.prompt.md)
- **Terraform:** [Lab 3 Terraform starter](../../.github/prompts/03-workbook-terraform.prompt.md)

Then use this implementation prompt:

```text
Read the Lab 3 requirements and approved design/integration-design.json.
Stop if the design is missing, invalid, or not approved.

Implement the approved design in my selected IaC track: the complete private
Logic App Standard foundation, approved integration resources and workload RBAC,
one workflow per processing tab, tested transformations and XRef lookups, Source
helper scripts, sanitized fixtures, and mocked external systems.

Preserve the host-storage and workload identity boundaries. Do not add unapproved
resources, real external-system connections, customer identifiers, or secrets.
Complete each input message only after its validated Output is published.

Before editing, explain the resource graph, identity boundaries, expected files,
costs, and validation commands. Wait for my approval. Then implement in dependency
order, run the selected track's format/build or validate checks, and review the
deployment preview with me before deploying.

Run each Source helper and verify expected outputs, correlation, and the
approved failure behavior at every workflow and broker handoff against mocks.
Document helper invocation, results, and cleanup.
```

**Done when:** deployed behavior matches the approved contracts and sanitized
fixtures, success and failure paths work, and no customer data or secrets are
committed or logged.

## Cleanup

Preview deletion first. Delete only the Lab 3-owned resource group for a
Bicep deployment or run `terraform destroy` for the selected Terraform
deployment. Leave existing systems and shared resources untouched.
