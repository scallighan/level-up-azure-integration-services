#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
track="${2:-}"
if [[ $# != 2 || ! "$action" =~ ^(setup|preview|deploy)$ ||
  ! "$track" =~ ^(bicep|terraform)$ ]]; then
  echo "Usage: $0 <setup|preview|deploy> <bicep|terraform>" >&2
  exit 2
fi

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

required=(az jq)
[[ "$track" != "terraform" ]] || required+=(terraform)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Missing required command: $command_name" >&2
    exit 1
  }
done

if [[ ! -f .env ]]; then
  if [[ "$action" != "setup" ]]; then
    echo "Missing .env. Run $0 setup $track first." >&2
    exit 1
  fi
  cp .env.example .env
fi

AZURE_SUBSCRIPTION_ID=""
WORKSHOP_PREFIX=""
AZURE_LOCATION=""
EXISTING_RESOURCE_GROUP_NAME=""
set -a
source .env
set +a

if [[ "$action" == "setup" ]]; then
  read -r -p "Azure subscription ID [$AZURE_SUBSCRIPTION_ID]: " answer
  AZURE_SUBSCRIPTION_ID="${answer:-$AZURE_SUBSCRIPTION_ID}"
  read -r -p "Workshop prefix [$WORKSHOP_PREFIX]: " answer
  WORKSHOP_PREFIX="${answer:-$WORKSHOP_PREFIX}"
  read -r -p "Azure region [$AZURE_LOCATION]: " answer
  AZURE_LOCATION="${answer:-$AZURE_LOCATION}"
  read -r -p "Existing resource group [${EXISTING_RESOURCE_GROUP_NAME:-create a workshop group}]: " answer
  EXISTING_RESOURCE_GROUP_NAME="${answer:-$EXISTING_RESOURCE_GROUP_NAME}"
fi

if [[ -z "$AZURE_SUBSCRIPTION_ID" ||
  ! "$WORKSHOP_PREFIX" =~ ^[a-z][a-z0-9]{2,11}$ ||
  ! "$AZURE_LOCATION" =~ ^[a-z][a-z0-9]+$ ]]; then
  echo "Set a subscription ID, a 3-12 character lowercase alphanumeric prefix starting with a letter, and a region identifier." >&2
  exit 1
fi

export TF_VAR_subscription_id="$AZURE_SUBSCRIPTION_ID"
export TF_VAR_prefix="$WORKSHOP_PREFIX"
export TF_VAR_location="$AZURE_LOCATION"
export TF_VAR_existing_resource_group_name="$EXISTING_RESOURCE_GROUP_NAME"

temporary_file=""
trap '[[ -z "$temporary_file" ]] || rm -f -- "$temporary_file"' EXIT

if [[ "$action" == "setup" ]]; then
  if ! az account show --output none; then
    echo "No active Azure session; signing in."
    az login --output none
  fi
fi
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
if [[ -n "$EXISTING_RESOURCE_GROUP_NAME" ]]; then
  az group show --subscription "$AZURE_SUBSCRIPTION_ID" \
    --name "$EXISTING_RESOURCE_GROUP_NAME" --query '{name:name,id:id}' --output table
fi

if [[ "$action" == "setup" ]]; then
  bash scripts/check-prereqs.sh "$track" "$AZURE_LOCATION"
  for provider in Microsoft.Network Microsoft.Storage Microsoft.ManagedIdentity \
    Microsoft.Web Microsoft.DocumentDB Microsoft.ServiceBus Microsoft.Insights \
    Microsoft.OperationalInsights; do
    az provider register --subscription "$AZURE_SUBSCRIPTION_ID" \
      --namespace "$provider" --wait
  done

  printf -v FOUNDATION_CONFIG_AZURE_SUBSCRIPTION_ID '%q' "$AZURE_SUBSCRIPTION_ID"
  printf -v FOUNDATION_CONFIG_WORKSHOP_PREFIX '%q' "$WORKSHOP_PREFIX"
  printf -v FOUNDATION_CONFIG_AZURE_LOCATION '%q' "$AZURE_LOCATION"
  printf -v FOUNDATION_CONFIG_EXISTING_RESOURCE_GROUP_NAME '%q' "$EXISTING_RESOURCE_GROUP_NAME"
  export FOUNDATION_CONFIG_AZURE_SUBSCRIPTION_ID FOUNDATION_CONFIG_WORKSHOP_PREFIX \
    FOUNDATION_CONFIG_AZURE_LOCATION FOUNDATION_CONFIG_EXISTING_RESOURCE_GROUP_NAME
  temporary_file="$(mktemp "$root/.env.XXXXXX")"
  awk '
    /^(AZURE_SUBSCRIPTION_ID|WORKSHOP_PREFIX|AZURE_LOCATION|EXISTING_RESOURCE_GROUP_NAME)=/ {
      split($0, parts, "=")
      print parts[1] "=" ENVIRON["FOUNDATION_CONFIG_" parts[1]]
      next
    }
    { print }
  ' .env > "$temporary_file"
  mv -- "$temporary_file" .env
  temporary_file=""
  echo "Setup saved in .env. Next: $0 preview $track"
  exit 0
fi

if [[ "$track" == "bicep" ]]; then
  deployment=(az deployment sub)
  parameters=(
    --subscription "$AZURE_SUBSCRIPTION_ID" --location "$AZURE_LOCATION"
    --template-file labs/00-foundation/iac/bicep/main.bicep
    --parameters "prefix=$WORKSHOP_PREFIX" "location=$AZURE_LOCATION"
    "existingResourceGroupName=$EXISTING_RESOURCE_GROUP_NAME"
  )
  if [[ "$action" == "preview" ]]; then
    az bicep format --file labs/00-foundation/iac/bicep/main.bicep
    az bicep format --file labs/00-foundation/iac/bicep/resources.bicep
    az bicep build --file labs/00-foundation/iac/bicep/main.bicep --stdout >/dev/null
    "${deployment[@]}" what-if "${parameters[@]}"
  else
    "${deployment[@]}" create "${parameters[@]}" \
      --name "foundation-$WORKSHOP_PREFIX" --output none
    temporary_file="$(mktemp "$root/.foundation.deployment.XXXXXX")"
    "${deployment[@]}" show --subscription "$AZURE_SUBSCRIPTION_ID" \
      --name "foundation-$WORKSHOP_PREFIX" \
      --query properties.outputs.foundation.value --output json > "$temporary_file"
  fi
else
  terraform_command=(terraform -chdir=labs/00-foundation/iac/terraform)
  if [[ "$action" == "preview" ]]; then
    "${terraform_command[@]}" init
    "${terraform_command[@]}" fmt -check
    "${terraform_command[@]}" validate
    "${terraform_command[@]}" plan
  else
    "${terraform_command[@]}" apply
    temporary_file="$(mktemp "$root/.foundation.deployment.XXXXXX")"
    "${terraform_command[@]}" output -json foundation > "$temporary_file"
  fi
fi

if [[ "$action" == "deploy" ]]; then
  if ! jq -e 'type == "object" and (.resource_group_name | type == "string" and length > 0)' \
    "$temporary_file" >/dev/null; then
    echo "Deployment did not return a valid foundation handoff; the previous handoff was not changed." >&2
    exit 1
  fi
  mv -- "$temporary_file" foundation.deployment.json
  temporary_file=""
  echo "Handoff saved to foundation.deployment.json."
fi
