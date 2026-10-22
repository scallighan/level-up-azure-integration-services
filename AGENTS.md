# Repository instructions

This repository is a half-day workshop about building Azure Integration
Services with GitHub Copilot. Favor clear teaching code over abstraction.

Keep things clean, clear and concise. 

Default `show_sample_payloads` to `true` for every workshop workflow, including
temporary helpers and workflows generated for later labs, so public teaching
inputs and outputs are visible in run history. Follow the
[run-history standards](docs/implementation-standards.md#sample-payload-visibility).
Keep `false` available and require it before processing real or sensitive data.

For workshop-owned Cosmos NoSQL containers, explicitly configure consistent
indexing, include `/*`, and exclude `/"_etag"/?` as described in the
[implementation standards](docs/implementation-standards.md#cosmos-db).
Keep both IaC tracks equivalent; later labs must not change shared containers.

Before proposing or making a change, read:

1. [`docs/implementation-standards.md`](docs/implementation-standards.md);
2. the active lab README and `implementation-requirements.md`;
3. the active lab contracts when present, or its available design plans; and
4. for Logic App infrastructure, `docs/logic-app-standard-baseline.md` and the
   matching implementation under `scallighan/logic-app-doc-processing`.

Treat those documents as mandatory context. The learner's current request
defines the bounded outcome; do not infer a numbered checkpoint or expand the
scope to later lab tasks. Before editing, explain the intended resource graph,
identity boundaries, expected files, and validation commands.
