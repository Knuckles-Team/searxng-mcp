# Code Enhancement: searxng-mcp

> Automated code enhancement review for searxng-mcp. Covers 17 analysis domains.

## User Stories

- As a **developer**, I want to **address Project Analysis findings (grade: C, score: 74)**, so that **improve project project analysis from C to at least B (80+)**.
- As a **developer**, I want to **address Test Coverage findings (grade: C, score: 75)**, so that **improve project test coverage from C to at least B (80+)**.
- As a **developer**, I want to **address Concept Traceability findings (grade: F, score: 31)**, so that **improve project concept traceability from F to at least B (80+)**.
- As a **developer**, I want to **address Test Execution findings (grade: F, score: 25)**, so that **improve project test execution from F to at least B (80+)**.
- As a **developer**, I want to **address Version Sync Analysis findings (grade: D, score: 60)**, so that **improve project version sync analysis from D to at least B (80+)**.
- As a **developer**, I want to **address Changelog Audit findings (grade: C, score: 75)**, so that **improve project changelog audit from C to at least B (80+)**.
- As a **developer**, I want to **address analyze_xdg_kg findings (grade: F, score: 0)**, so that **improve project analyze_xdg_kg from F to at least B (80+)**.

## Functional Requirements

- **FR-001**: Minor update: pytest-xdist 3.6.0 (constraint — not installed) -> 3.8.0
- **FR-002**: Minor update: agent-utilities 0.2.40 (installed) -> 0.16.0
- **FR-003**: Test suite lacks intent diversity (only one type)
- **FR-004**: 12 potential doc-test drift items
- **FR-005**: README.md missing sections: usage|quick start
- **FR-006**: 2 broken internal links in README.md
- **FR-007**: README missing: Has a Table of Contents
- **FR-008**: README missing: Has usage examples with code blocks
- **FR-009**: No discernible layer architecture (no domain/service/adapter separation)
- **FR-010**: Low traceability ratio: 0% concepts fully traced
- **FR-011**: 17 orphaned concepts (only in one source)
- **FR-012**: 6 concepts with drift (missing from one source)
- **FR-013**: 7 test functions missing concept markers
- **FR-014**: Total lint findings: 0 (high/error: 0, medium/warning: 0, low: 0)
- **FR-015**: 2 hook(s) may be outdated: ruff-pre-commit, uv-pre-commit
- **FR-016**: 1 rogue/throwaway scripts detected (fix_*, validate_*, patch_*, etc.): scripts/validate_a2a_agent.py
- **FR-017**: Found 5 file(s) with version '0.14.0' that are NOT tracked in .bumpversion.cfg:
- **FR-018**:   - .specify/searxng-mcp/results.json
- **FR-019**:   - .specify/specs/code-enhancement-20260522/tasks.json
- **FR-020**:   - .specify/specs/code-enhancement-20260522/tasks.md
- **FR-021**:   - .specify/specs/code-enhancement-20260522/spec.md
- **FR-022**:   - .specify/specs/code-enhancement-20260522/spec.json
- **FR-023**: CHANGELOG.md exists but could not be parsed — check format compliance
- **FR-024**: No changelog entries within the last 30 days
- **FR-025**: keepachangelog not installed — pip install 'universal-skills[code-enhancer]'
- **FR-026**: No shared fixtures in conftest.py
- **FR-027**: 1 tests have no assertions
- **FR-028**: Partial env var documentation: 38% coverage
- **FR-029**: Undocumented env vars: AUTH_TYPE, EUNOMIA_POLICY_FILE, EUNOMIA_TYPE, OTEL_EXPORTER_OTLP_ENDPOINT, SEARXNG_INSTANCE_URL, SEARXNG_PASSWORD, SEARXNG_USERNAME, USE_RANDOM_INSTANCE
- **FR-030**: Analysis error: No module named 'agent_utilities.knowledge_graph'

## Success Criteria

- Overall GPA: 2.59 → 3.0
- Domains at B or above: 10 → 17
- Actionable findings: 30 → 0
