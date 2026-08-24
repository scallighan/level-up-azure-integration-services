#!/usr/bin/env bash
set -euo pipefail

required_files=(
  ".github/copilot-instructions.md"
  "docs/prerequisites.md"
  "labs/01-crud-integration/contracts/openapi.yaml"
  "labs/02-topic-fanout/contracts/order-created.schema.json"
  "labs/02-topic-fanout/contracts/sample-order-created.json"
)

for file in "${required_files[@]}"; do
  [[ -s "$file" ]] || {
    echo "Missing or empty workshop file: $file" >&2
    exit 1
  }
done

jq empty labs/02-topic-fanout/contracts/order-created.schema.json
jq empty labs/02-topic-fanout/contracts/sample-order-created.json

if grep -RInE \
  '(AccountKey=|SharedAccessKey=|sig=[A-Za-z0-9%]|-----BEGIN (RSA |EC )?PRIVATE KEY-----)' \
  --exclude='validate-workshop.sh' .; then
  echo "Potential secret material found." >&2
  exit 1
fi

echo "Workshop structure and JSON contracts are valid."
