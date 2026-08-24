# Agentic Azure Integration Services Development

A half-day, hands-on workshop for using GitHub Copilot to design, provision,
review, and operate Azure Integration Services solutions.

**Workshop site:** <https://scallighan.github.io/level-up-azure-integration-services/>

Participants build the same solutions with either **Bicep** or **Terraform**:

1. A CRUD application using Azure Static Web Apps, Logic Apps, and Azure Cosmos
   DB, with optional new or existing API Management.
2. An event fan-out solution using an Azure Service Bus topic and three Logic
   App subscribers.

The workshop emphasizes the engineering loop around Copilot: provide context,
ask for a small change, review the result, validate it with native tools, and
iterate. Copilot accelerates the work; Azure documentation, deployment previews,
and test results remain the source of truth.

## Workshop at a glance

| Section | Time | Outcome |
|---|---:|---|
| Setup and Copilot context | 30 min | Tools verified and repository context loaded |
| Lab 1: CRUD integration | 90 min | Browser-to-database request path deployed and tested |
| Break | 15 min | |
| Lab 2: topic fan-out | 75 min | One event independently processed by three workflows |
| Review and cleanup | 30 min | IaC reviewed, resources removed, takeaways captured |

## Start here

1. Complete [the prerequisites](docs/prerequisites.md).
2. Read the [Copilot working agreement](docs/copilot-working-agreement.md).
3. Choose one IaC track for the day: **Bicep** or **Terraform**.
4. Complete [Lab 1](labs/01-crud-integration/README.md).
5. Complete [Lab 2](labs/02-topic-fanout/README.md).
6. Delete workshop resources using the cleanup steps in each lab.

Instructors should also read the [instructor guide](docs/instructor-guide.md).
People assisting learners should use the
[coaches guide](docs/coaches-guide.md).

## Repository layout

```text
.github/
  copilot-instructions.md       Repository-wide Copilot context
  prompts/                      Reusable workshop prompt files
docs/                           Setup and facilitation guidance
labs/
  01-crud-integration/          Static Web Apps -> optional APIM -> Logic Apps
  02-topic-fanout/              Service Bus topic -> three Logic Apps
scripts/                        Local workshop checks
```

## Source material

The Logic App hosting foundation must replicate the matching working
[Bicep](https://github.com/scallighan/logic-app-doc-processing/tree/main/bicep)
or
[Terraform](https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform)
implementation in `scallighan/logic-app-doc-processing`. See the
[Logic App Standard infrastructure baseline](docs/logic-app-standard-baseline.md)
for the exact workshop boundary. The reference project's SQL, Document
Intelligence, and Office 365 resources remain capstone material and are not
implicitly part of these labs.

## Cost and safety

The labs create billable Azure resources. Use a non-production subscription,
choose the lowest practical SKUs, never commit secrets or Terraform state, and
run each lab's cleanup steps when finished.