# Lab 1 instructions

Read the [README](README.md), [implementation requirements](implementation-requirements.md),
and [OpenAPI contract](contracts/openapi.yaml) before changing this lab.

Reuse the prepared `lab01Cosmos` built-in connection. Keep
`authProvider.Type = ManagedServiceIdentity` **inside `parameterValues`**,
never at the connection's top level. Use the site's system-assigned identity,
not the host-storage user-assigned identity.

Before deploying workflow artifacts, follow the required
[Cosmos authentication checks](implementation-requirements.md#cosmos-authentication-checks).
Do not change RBAC, networking, or authentication methods to work around
a malformed connection definition.
