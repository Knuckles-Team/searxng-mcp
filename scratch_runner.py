import importlib.util
import json
import time
from pathlib import Path

scripts_dir = Path("/home/genius/.gemini/antigravity/skills/code-enhancer/scripts")
project_dir = "/home/apps/workspace/agent-packages/agents/searxng-mcp"

analyzers = [
    ("analyze_project", "analyze_project"),
    ("audit_dependencies", "audit_dependencies"),
    ("analyze_codebase", "analyze_codebase"),
    ("analyze_security", "analyze_security"),
    ("analyze_tests", "analyze_tests"),
    ("audit_documentation", "audit_documentation"),
    ("analyze_architecture", "analyze_architecture"),
    ("trace_concepts", "trace_concepts"),
    ("run_linters", "run_linters"),
    ("run_precommit", "run_precommit"),
    ("run_tests", "run_tests"),
    ("analyze_directory_density", "analyze_directory_density"),
    ("analyze_ui", "analyze_ui"),
    ("analyze_version_sync", "analyze_version_sync"),
    ("audit_changelog", "audit_changelog"),
    ("grade_pytest", "grade_pytest"),
    ("scan_env_vars", "scan_env_vars"),
]

results = []

for module_name, func_name in analyzers:
    print(f"Running {module_name}...", flush=True)
    try:
        spec = importlib.util.spec_from_file_location(
            module_name, str(scripts_dir / f"{module_name}.py")
        )
        if spec is None or spec.loader is None:
            print(f"  -> Spec/loader not found for {module_name}", flush=True)
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        func = getattr(mod, func_name)

        start = time.monotonic()
        result = func(project_dir)
        elapsed = time.monotonic() - start
        print(
            f"  -> Success in {elapsed:.2f}s, score: {result.get('score')}", flush=True
        )
        results.append(result)
    except Exception as e:
        print(f"  -> ERROR running {module_name}: {e}", flush=True)

print("\nGenerating report...", flush=True)
import generate_report

report_path = "/home/apps/workspace/reports/code-enhancer-searxng/report.md"
generate_report.generate_report(
    results, project_name="searxng-mcp", output_path=report_path
)
print(f"Report saved to {report_path}", flush=True)

# Save results.json
results_json_path = "/home/apps/workspace/reports/code-enhancer-searxng/results.json"
Path(results_json_path).parent.mkdir(parents=True, exist_ok=True)
with open(results_json_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"Results JSON saved to {results_json_path}", flush=True)

print("Generating SDD handoff...", flush=True)
import generate_sdd_handoff

handoff = generate_sdd_handoff.generate_sdd_handoff(
    results, project_name="searxng-mcp", output_dir=project_dir
)
print("SDD handoff generated successfully inside .specify/specs/", flush=True)
print("All done!", flush=True)
