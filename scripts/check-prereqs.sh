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

az account show --query '{subscription:name, tenant:tenantId}' --output table
gh auth status
if [[ "$track" == "bicep" ]]; then
  az bicep version
fi
echo "Prerequisites are available for the $track track."
