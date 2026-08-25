#!/usr/bin/env bash
set -euo pipefail

track="${1:-}"
if [[ "$track" != "bicep" && "$track" != "terraform" ]]; then
  echo "Usage: $0 <bicep|terraform>" >&2
  exit 2
fi

required=(az gh git jq)
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

suggest_ws1_region() {
  local api_version="2026-07-15"
  local display_name region usage current limit
  local -a catalog_regions=()
  local -a preferred_regions=(
    eastus2
    centralus
    eastus
    northcentralus
    southcentralus
    westcentralus
    westus2
    westus3
    westus
    canadacentral
    canadaeast
    northeurope
    westeurope
    uksouth
    ukwest
  )
  declare -A supported_regions=()
  declare -A checked_regions=()

  while IFS= read -r display_name; do
    [[ "$display_name" == *"(Stage)"* ]] && continue
    region="$(tr '[:upper:]' '[:lower:]' <<<"$display_name" | tr -d ' ')"
    catalog_regions+=("$region")
    supported_regions["$region"]=1
  done < <(az appservice list-locations --sku WS1 --query '[].name' --output tsv)

  for region in "${preferred_regions[@]}" "${catalog_regions[@]}"; do
    [[ -n "${supported_regions[$region]:-}" ]] || continue
    [[ -z "${checked_regions[$region]:-}" ]] || continue
    checked_regions["$region"]=1

    usage="$(
      az rest \
        --method get \
        --url "https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Web/locations/$region/usages?api-version=$api_version" \
        --query "value[?name.value == 'WS1'].[currentValue, limit] | [0]" \
        --output tsv 2>/dev/null || true
    )"
    read -r current limit <<<"$usage"

    if [[ "$current" =~ ^[0-9]+$ && "$limit" =~ ^[0-9]+$ ]] &&
      ((limit - current >= 1)); then
      echo "Suggested WS1 region: $region ($((limit - current)) worker available)."
      return
    fi
  done

  echo "No catalog-supported region with available WS1 quota was found." >&2
  echo "Request at least 1 WS1 VM from App Service (Microsoft.Web) quotas." >&2
  return 1
}

az account show --query '{subscription:name, tenant:tenantId}' --output table
ws1_capacity_available=true
if ! suggest_ws1_region; then
  ws1_capacity_available=false
fi
gh auth status
if [[ "$track" == "bicep" ]]; then
  az bicep version
fi

if [[ "$ws1_capacity_available" != true ]]; then
  exit 1
fi

echo "Prerequisites are available for the $track track."
