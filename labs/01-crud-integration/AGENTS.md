# Lab 1 instructions

Read the [README](README.md), [implementation requirements](implementation-requirements.md),
and [OpenAPI contract](contracts/openapi.yaml) before changing this lab.

Name the workflow `lab01-workflow`. Keep the OpenAPI logical operation
`POST /region-lookup` unchanged; use the workflow's new callback URL.

Reuse the prepared `lab01Cosmos` built-in connection. Keep
`authProvider.Type = ManagedServiceIdentity` **inside `parameterValues`**,
never at the connection's top level. Use the site's system-assigned identity,
not the host-storage user-assigned identity.

Before deploying workflow artifacts, follow the required
[Cosmos authentication checks](implementation-requirements.md#cosmos-authentication-checks).
Do not change RBAC, networking, or authentication methods to work around
a malformed connection definition.

## Runtime guardrails

- Follow the [runtime validation guardrails](implementation-requirements.md#runtime-validation-guardrails).
  `ParseJson` rejects `pattern` and `patternProperties`. Keep OpenAPI unchanged
  and enforce its key rules with the documented native XPath/boolean guards.
- Use native actions, not `JavaScriptCode`, for this lab's validation.
  Do not change the shared host to work around an inline-code worker failure.
- Apply the [supported run-history protection](implementation-requirements.md#supported-run-history-protection)
  when `show_sample_payloads=false`. Default this input to `true` for public
  teaching data, omitting `secureData` so inputs/outputs are visible. Never emit
  empty protection arrays. Require `false` before using real or sensitive data;
  `ParseJson`, `Compose`, and `Response` then use Secure Inputs only.
  Never change authentication or networking.
- Verify [native runtime readiness](implementation-requirements.md#native-runtime-readiness),
  not just artifact deployment or ARM file-view health, before HTTP tests.
  Require live contract checks and successful statuses for both Cosmos reads.
- Report the [known malformed-JSON boundary](implementation-requirements.md#known-malformed-json-boundary)
  as an unmet contract limitation. Do not change the contract, test content type,
  or infrastructure to make that case appear to pass.
