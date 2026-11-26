---
name: searxng-mcp-development
skill_type: skill
description: >-
  Develop and validate searxng-mcp within the shared connector and spec-delivery
  contracts.
license: MIT
tags: [searxng, development, mcp, spec-delivery]
metadata:
  author: Knuckles-Team
  version: '0.1.0'
---

# SearXNG MCP Development

Use this skill when changing the `searxng-mcp` connector, its documentation, or
its spec-delivery integration. Work from the repository root and read `AGENTS.md`,
the affected module, and the relevant `specs/` status before editing. Keep the
connector focused on the SearXNG MCP and A2A surfaces; graph facts and ontology
ownership remain with the existing connector and engine contracts.

## Steps

1. Read `AGENTS.md` and the affected module, and find the owning requirement with `git grep -n "<term>" -- specs`.
   Verify a row matches before editing.
2. Make the change within the connector boundary under `searxng_mcp/`.
   Verify it reuses existing connector and SDK pieces and adds no parallel framework.
3. Run the narrowest relevant test with `uv run pytest -q`.
   Verify it passes.
4. Run the hooks with `pre-commit run --all-files`.
   Verify every hook reports Passed.
5. Stage reviewed paths with `git add -- <path>` and inspect `git diff --cached --name-status`.
   Verify only intended files are listed before committing with a `Spec:` trailer.

## Failure recovery

| Failure | Cause | Recovery |
|---------|-------|----------|
| A hook fails | Formatting, spelling or a gate was violated | Read the hook output, fix the named file, and rerun `pre-commit run --all-files` |
| Generated spec status shows as modified | It was hand-edited | Restore it with `git checkout -- <path>` for that file, and let the central pipeline tools regenerate it |
| No spec row matches | The behavior is not yet specified | Extend the closest row in `specs` first, and cite its id in the `Spec:` trailer |

## Rapid delivery: the 5-minute contract

For a small, reviewable change:

1. Identify one requirement or maintenance slice and name the exact files it touches.
2. Reuse the existing connector, SDK, central pipelines, and package conventions. Do
   not add a local planner, CI framework, publisher, or parallel transport.
3. Keep spec status generated from the canonical pipeline tools. Run the focused tests
   for the changed behavior, then run `pre-commit run --all-files` from the repo root.
4. Review the complete diff, including workflow and package-data changes, and record
   the source revision plus the commands and results used as evidence.
5. Keep credentials, generated output, caches, and scratch files outside the checkout.
   A Pages claim is complete only after the central reusable workflow has run and the
   exact published `spec-delivery/` source can be checked.

### Change boundaries

- Preserve the existing SearXNG runtime, MCP tools, A2A surface, and source ontology
  files; central release tooling owns generated certification and connector-shape
  artifacts.
- Extend an existing spec or connector operation before adding a new abstraction.
- Use the central Pages workflow and `.config/spec-dashboard.json` for the spec
  dashboard; keep one documentation publisher for this repository.
- Keep the central aggregate hooks in `.pre-commit-config.yaml`; do not copy their
  implementation or create a second CI framework.

### Validation evidence

For code changes, run the narrowest relevant test first and then the repository hooks.
For delivery changes, validate JSON and YAML syntax and inspect the rendered dashboard
inputs before requesting review. Report failures with the command, revision, and file
or line that needs attention; do not hide a failing check behind a skipped hook.
