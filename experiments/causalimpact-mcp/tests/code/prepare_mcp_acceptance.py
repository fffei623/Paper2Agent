import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
fixture = json.loads((root / "tests/data/vignette-input.json").read_text(encoding="utf-8"))
if fixture.get("model_args") == []:
    fixture.pop("model_args")
root_out = (root / "tests/results/tool-runs").resolve()
cases = [
    {
        "name": "official-vignette-new-input",
        "tool": "analyze_causal_impact",
        "arguments": fixture,
        "required_inputs": ["data", "post_period", "pre_period"],
        "expected_subset": {
            "package_version": "1.4.1",
            "pre_period": [1, 70],
            "post_period": [71, 100],
            "alpha": 0.05,
        },
        "min_artifacts": 2,
        "artifact_root": str(root_out),
        "unique_artifacts": True,
    },
    {
        "name": "reject-short-series",
        "tool": "analyze_causal_impact",
        "arguments": {"data": [[1.0], [2.0], [3.0]], "pre_period": [1, 2], "post_period": [3, 3]},
        "required_inputs": ["data", "post_period", "pre_period"],
        "error_contains": "at least four rows",
    },
]
(root / "reports/mcp-acceptance-cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
(root / "reports/expected-mcp-tools.json").write_text(json.dumps(["analyze_causal_impact"], indent=2), encoding="utf-8")
