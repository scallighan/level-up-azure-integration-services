# Copilot working agreement

## The loop

Use the same loop for every exercise:

1. **Context** — open the lab README, relevant source files, and
   both `AGENTS.md` and `.github/copilot-instructions.md`.
2. **Prompt** — request one bounded change with resources, constraints, and
   acceptance criteria.
3. **Review** — inspect every proposed file and ask Copilot to explain unfamiliar
   code.
4. **Validate** — format, lint, preview, and test with the native toolchain.
5. **Iterate** — paste the exact error and relevant code back into Copilot; do
   not ask it to guess.
6. **Commit** — save a small, working change.

## Prompt pattern

```text
Goal:
Create <one bounded outcome>.

Context:
- Read <files>.
- Use <existing conventions/helpers>.

Constraints:
- Use managed identity; do not use account keys.
- Put configurable values in parameters/variables.
- Use the lowest workshop-appropriate SKU.
- Keep Bicep and Terraform behavior equivalent.

Acceptance criteria:
- <native format/validate command> passes.
- Deployment preview contains only the expected resource types.
- Outputs expose only non-secret values needed by the next step.

Before editing:
Summarize the proposed resource graph and identify any uncertain API versions,
provider behavior, or security assumptions.
```

## Productive Copilot requests

- “Explain this deployment preview and call out destructive replacements.”
- “Compare these Bicep and Terraform resource graphs for behavioral drift.”
- “Write a test request from this OpenAPI operation and explain the expected
  status code.”
- “Find every place this resource name is coupled to another file.”
- “Review this Logic App definition for secret leakage, replay behavior, and
  duplicate message handling.”

Avoid broad requests such as “build the entire lab.” Smaller requests are easier
to verify and teach participants how to retain control.

## Invoking workshop prompt files

The four lab-and-track files under `.github/prompts/` are one-time starter
prompts. Invoke the selected prompt from the repository root so its relative
paths and repository-wide instructions resolve correctly. It creates the
selected IaC directory, minimal base files, and a path-local `AGENTS.md`; it
does not implement a numbered lab task.

In VS Code Copilot Chat, select **Agent** mode and enter the prompt filename
without `.prompt.md` as a slash command:

```text
/01-crud-terraform
```

In GitHub Copilot CLI, start `copilot` from the repository root and use `@` to
mention the prompt file:

```text
@.github/prompts/01-crud-terraform.prompt.md
```

The prompt file is not executed by Bash or Terraform. Copilot reads it as the
starter task. Review its proposed file structure and generated files. Then use
the task-specific prompt in the lab README for the next bounded outcome instead
of appending a numbered task to the starter invocation.

## Review checklist

Do not deploy until you can answer:

- Which identities access which resources?
- Where are secrets or callback URLs stored?
- What makes names globally unique?
- What happens when a request or message is retried?
- Which resources can incur material cost?
- Does the deployment preview match the intended architecture?
- Can the deployment and cleanup be repeated safely?
