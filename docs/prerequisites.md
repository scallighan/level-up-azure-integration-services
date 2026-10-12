# Setup has moved to Lab 0

Start with [Lab 0: Shared Azure foundation](../labs/00-foundation/README.md).
It includes workstation tools, Azure sign-in and provider registration, region
and WS1 quota checks, the choice of an existing or new resource group, and
complete Bicep or Terraform deployments.

Lab 0 creates the shared Logic App Standard hosting, private Cosmos DB,
Service Bus Standard namespace, and Application Insights/Log Analytics once.
Labs 1-3 reuse its non-secret handoff instead of generating their own hosting
foundations.

Use a non-production subscription. APIM remains optional; instructors should
prefer a shared existing non-production instance if demonstrating that
extension. Confirm its SKU and participant permissions in advance.
