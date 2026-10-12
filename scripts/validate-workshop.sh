#!/usr/bin/env bash
set -euo pipefail

required_files=(
  ".github/copilot-instructions.md"
  ".github/workflows/pages.yml"
  "_config.yml"
  "_layouts/default.html"
  "assets/css/style.scss"
  "docs/coaches-guide.md"
  "docs/implementation-standards.md"
  "docs/logic-app-standard-baseline.md"
  "docs/prerequisites.md"
  "index.md"
  "labs/00-foundation/README.md"
  "labs/00-foundation/implementation-requirements.md"
  "labs/00-foundation/iac/bicep/main.bicep"
  "labs/00-foundation/iac/bicep/resources.bicep"
  "labs/00-foundation/iac/terraform/main.tf"
  "labs/00-foundation/iac/terraform/variables.tf"
  "labs/00-foundation/iac/terraform/providers.tf"
  "labs/00-foundation/iac/terraform/versions.tf"
  "labs/00-foundation/iac/terraform/outputs.tf"
  "scripts/verify-foundation.sh"
  "scripts/test_verify_foundation.py"
  "labs/01-crud-integration/implementation-requirements.md"
  "labs/01-crud-integration/contracts/openapi.yaml"
  "labs/02-topic-fanout/implementation-requirements.md"
  "labs/02-topic-fanout/contracts/order-created.schema.json"
  "labs/02-topic-fanout/contracts/sample-order-created.json"
  "labs/03-workbook-to-solution/README.md"
  "labs/03-workbook-to-solution/implementation-requirements.md"
  "scripts/extract-integration-workbook.py"
)

for file in "${required_files[@]}"; do
  [[ -s "$file" ]] || {
    echo "Missing or empty workshop file: $file" >&2
    exit 1
  }
done

jq empty labs/02-topic-fanout/contracts/order-created.schema.json
jq empty labs/02-topic-fanout/contracts/sample-order-created.json
bash -n scripts/verify-foundation.sh
PYTHONDONTWRITEBYTECODE=1 python scripts/test_verify_foundation.py
PYTHONPYCACHEPREFIX="${TMPDIR:-/tmp}/level-up-azure-integration-services-pycache" \
  python -m py_compile scripts/extract-integration-workbook.py

if grep -RInE \
  '(AccountKey=|SharedAccessKey=|sig=[A-Za-z0-9%]|-----BEGIN (RSA |EC )?PRIVATE KEY-----)' \
  --exclude='validate-workshop.sh' \
  --exclude='*.tfstate' \
  --exclude='*.tfstate.*' \
  --exclude-dir='.terraform' .; then
  echo "Potential secret material found." >&2
  exit 1
fi

echo "Workshop structure and JSON contracts are valid."
