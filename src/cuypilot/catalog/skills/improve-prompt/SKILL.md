---
name: improve-prompt
description: Turn a rough or vague request into a clear, complete prompt for Copilot (goal, context, scope, constraints, done criteria, output format) before any work starts. Only runs when the user explicitly invokes /improve-prompt.
argument-hint: <your rough request>
disable-model-invocation: true
---

# Improve prompt

Goal: rewrite the user's rough request into a prompt that an agent can execute well on the first try. **Do not execute the task.** Only produce the improved prompt.

## Workflow

1. **Read the rough request** (the text after `/improve-prompt`). If it is empty, ask for it.
2. **Gather context yourself before asking.** Look at the workspace to fill gaps: files or modules mentioned, the stack (`pyproject.toml`, `requirements*.txt`, Databricks bundle/config files, notebooks), existing tests, conventions in `.github/copilot-instructions.md`. Use exact file paths and names you actually found.
3. **Check what the prompt is missing:**
   - **Goal:** what outcome is wanted and why (bug fix, refactor, new feature, optimization, documentation, analysis).
   - **Context:** relevant files, functions, tables, data sizes, Databricks runtime/cluster or Spark version if performance matters.
   - **Scope:** what is in and what must not be touched (public APIs, other modules, production tables).
   - **Constraints:** libraries allowed, Python version, style rules, performance or cost limits.
   - **Done criteria:** how to verify the result (tests pass, same output as before, query under N minutes, docs build).
   - **Output:** what to deliver (code change, plan only, review findings, explanation) and its format.
4. **Ask only what you cannot infer.** At most 3 short questions, each with a suggested default answer. If the gaps are minor, skip the questions and state your assumptions instead.
5. **Write the improved prompt** in the user's language, in a single fenced block, using this structure (omit empty sections):

```
## Goal
## Context
## Scope (in / out)
## Constraints
## Done when
## Deliverable
```

6. **After the block**, list in 2-4 bullets what you added or clarified, and offer to run it ("¿Lo ejecuto?").

## Rules

- Keep the user's intent; do not add features or scope they did not ask for.
- Prefer concrete references (paths, function names, table names) over generic wording.
- Keep it as short as possible while complete; a good prompt is usually 5-15 lines.
- For multi-step or risky work (large refactors, production data), suggest asking for a plan first.
