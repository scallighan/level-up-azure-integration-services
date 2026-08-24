# Prerequisites

## Access

- An Azure subscription where you can create resource groups, role assignments,
  Logic Apps, Cosmos DB, Service Bus, and Static Web Apps.
- If using API Management, permission to create an instance or to create APIs
  and policies in an existing instance.
- A GitHub account with access to GitHub Copilot.
- A local clone of this repository.

Use a workshop or development subscription. Do not deploy these exercises into
a production tenant.

## Tools

Install:

- [Git](https://git-scm.com/)
- [GitHub CLI](https://cli.github.com/)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [Visual Studio Code](https://code.visualstudio.com/) with GitHub Copilot and
  the extension for your chosen IaC language
- Bicep CLI through Azure CLI (`az bicep install`) **or**
  [Terraform](https://developer.hashicorp.com/terraform/install)
- `jq`

Sign in and select the intended subscription:

```bash
gh auth login
az login
az account set --subscription "<subscription-id-or-name>"
az account show --query '{name:name, id:id, tenantId:tenantId}' --output table
```

Check the workstation:

```bash
./scripts/check-prereqs.sh bicep
# or
./scripts/check-prereqs.sh terraform
```

## Azure provider registration

Provider registration can take several minutes. Register these before the
workshop:

```bash
for provider in \
  Microsoft.DocumentDB \
  Microsoft.Logic \
  Microsoft.ServiceBus \
  Microsoft.Web; do
  az provider register --namespace "$provider" --wait
done
```

Register `Microsoft.ApiManagement` only if using the new or existing APIM mode:

```bash
az provider register --namespace Microsoft.ApiManagement --wait
```

## Local configuration

Use one short, globally distinctive prefix throughout both labs, such as your
initials plus a number. Never place credentials, callback URLs, access keys,
Terraform state, or populated parameter files in Git.

Suggested values:

| Setting | Example |
|---|---|
| Prefix | `sc42` |
| Location | `eastus2` |
| Environment | `workshop` |
| Tags | `workshop=agentic-ais`, `owner=<alias>` |

## Before attendees arrive

The default lab mode does not use API Management. If demonstrating APIM,
instructors should prefer a shared existing non-production instance and grant
participants rights to create only their own API and policies. Confirm the
chosen SKU is available before offering the new-instance mode.
