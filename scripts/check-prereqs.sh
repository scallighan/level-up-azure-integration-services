#!/usr/bin/env bash
set -euo pipefail

track="${1:-}"
location="${2:-}"
if [[ $# != 2 || ( "$track" != "bicep" && "$track" != "terraform" ) ||
  ! "$location" =~ ^[a-z][a-z0-9]+$ ]]; then
  echo "Usage: $0 <bicep|terraform> <azure-region>" >&2
  exit 2
fi

required=(az jq)
if [[ "$track" == "terraform" ]]; then
  required+=(terraform)
fi

missing=()
for command_name in "${required[@]}"; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    missing+=("$command_name")
  fi
done

if ((${#missing[@]})); then
  printf 'Missing required command: %s\n' "${missing[@]}" >&2
  exit 1
fi

az account show --query '{subscription:name, tenant:tenantId}' --output table
if [[ "$track" == "bicep" ]]; then
  az bicep version
else
  version="$(terraform version -json | jq -r .terraform_version)"
  if [[ "$version" != "1.14.4" ]]; then
    echo "This workshop requires Terraform 1.14.4; found $version." >&2
    exit 1
  fi
fi

locations="$(az appservice list-locations --sku WS1 --query '[].name' --output tsv)"
supported=false
while IFS= read -r display_name; do
  [[ "$display_name" == *"(Stage)"* ]] && continue
  region="$(tr '[:upper:]' '[:lower:]' <<<"$display_name" | tr -d ' ')"
  if [[ "$region" == "$location" ]]; then
    supported=true
    break
  fi
done <<<"$locations"

if [[ "$supported" != true ]]; then
  echo "Windows WS1 is not available in $location. Choose a region from:" >&2
  printf '%s\n' "$locations" >&2
  exit 1
fi

if ! usage="$(az rest --method get \
  --url "https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Web/locations/$location/usages?api-version=2026-07-15" \
  --query "value[?name.value == 'WS1'] | [0].{current:currentValue,limit:limit}" --output json)"; then
  echo "Unable to check WS1 quota in $location. Resolve the Azure error above." >&2
  exit 1
fi
if ! quota="$(jq -er '
  select(type == "object") | [.current, .limit] |
  select(all(.[]; type == "number" and . >= 0 and floor == .)) | @tsv
' <<<"$usage")"; then
  echo "Azure did not return WS1 quota for $location. Confirm App Service quotas before deploying." >&2
  exit 1
fi
read -r current limit <<<"$quota"
if ((limit - current < 1)); then
  echo "No WS1 capacity remains in $location. Request at least one WS1 worker or choose another region." >&2
  exit 1
fi

echo "Ready for $track in $location: $((limit - current)) WS1 worker(s) available."
