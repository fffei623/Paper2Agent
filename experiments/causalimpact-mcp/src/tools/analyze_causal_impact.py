"""对固定版本 CausalImpact R 包的轻量 MCP 封装。"""
from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[2]
R_SCRIPT = PROJECT_ROOT / "src" / "r_scripts" / "analyze_causal_impact.R"
DEFAULT_RSCRIPT = PROJECT_ROOT / "r-runtime" / "R-4.6.2" / "bin" / "Rscript.exe"
DEFAULT_R_PROJECT = PROJECT_ROOT
ARTIFACT_ROOT = PROJECT_ROOT / "tests" / "results" / "tool-runs"
mcp = FastMCP("causalimpact-mcp")


def _validate(data: list[list[float | None]], pre_period: list[int], post_period: list[int],
              alpha: float, model_args: dict[str, Any] | None, seed: int | None) -> None:
    if len(data) < 4:
        raise ValueError("data must contain at least four rows")
    width = len(data[0]) if data else 0
    if width < 1 or any(len(row) != width for row in data):
        raise ValueError("data must be rectangular with response in column 1")
    for row in data:
        for j, value in enumerate(row):
            if value is None and j == 0:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("data values must be finite numbers; null is allowed only in response")
    for name, period in (("pre_period", pre_period), ("post_period", post_period)):
        if len(period) != 2 or any(isinstance(v, bool) or not isinstance(v, int) for v in period):
            raise ValueError(f"{name} must contain two integer row indices (1-based)")
        if period[0] < 1 or period[1] > len(data) or period[0] > period[1]:
            raise ValueError(f"{name} must lie within the 1-based data row range")
    if pre_period[1] >= post_period[0]:
        raise ValueError("pre_period must end before post_period begins")
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be strictly between 0 and 1")
    allowed = {"niter", "standardize.data", "prior.level.sd", "nseasons",
               "season.duration", "dynamic.regression", "max.flips"}
    if model_args and set(model_args) - allowed:
        raise ValueError(f"unsupported model_args: {sorted(set(model_args) - allowed)}")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer or null")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


@mcp.tool()
def analyze_causal_impact(
    data: list[list[float | None]], pre_period: list[int], post_period: list[int],
    alpha: float = 0.05, model_args: dict[str, Any] | None = None,
    seed: int | None = None, column_names: list[str] | None = None,
) -> dict[str, Any]:
    """使用 CausalImpact 分析干预效果。每行对应一个时间点，第一列为响应序列，其余列为控制序列。
    区间端点采用包含端点的 1 起始行号。因果解释依赖控制序列未受干预影响且前后关系稳定等假设。"""
    _validate(data, pre_period, post_period, alpha, model_args, seed)
    if column_names is not None and (len(column_names) != len(data[0]) or len(set(column_names)) != len(column_names)):
        raise ValueError("column_names must be unique and match the number of columns")
    run_id = uuid.uuid4().hex
    run_dir = ARTIFACT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    input_path = run_dir / "input.json"
    payload = {"data": data, "pre_period": pre_period, "post_period": post_period,
               "alpha": alpha, "model_args": model_args or {}, "seed": seed,
               "column_names": column_names}
    input_path.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    r_project = Path(os.environ.get("P2A_R_PROJECT", str(DEFAULT_R_PROJECT))).resolve()
    if not (r_project / "renv" / "activate.R").is_file():
        raise RuntimeError(f"R project is missing renv/activate.R: {r_project}")
    env = os.environ.copy()
    temp_root = Path(os.environ.get("P2A_R_TEMP_DIR", str(PROJECT_ROOT / "tmp" / "r"))).resolve()
    # Windows 版 R 不接受含空格的 R_TempDir；项目路径含空格时，改用最近的不含空格的上级目录。
    if os.name == "nt" and " " in str(temp_root):
        ancestor = PROJECT_ROOT.resolve()
        while " " in str(ancestor) and ancestor.parent != ancestor:
            ancestor = ancestor.parent
        temp_root = ancestor / ".paper2agent-r-tmp" / PROJECT_ROOT.name
    temp_root.mkdir(parents=True, exist_ok=True)
    env["TMPDIR"] = str(temp_root.resolve())
    env["TEMP"] = env["TMPDIR"]
    env["TMP"] = env["TMPDIR"]
    env["RENV_PROJECT"] = str(r_project)
    renv_cache = r_project / "renv" / "cache"
    renv_cache.mkdir(parents=True, exist_ok=True)
    env.setdefault("RENV_PATHS_ROOT", str(renv_cache.resolve()))
    rscript_value = os.environ.get("P2A_RSCRIPT")
    if rscript_value:
        rscript = Path(rscript_value).resolve()
    elif DEFAULT_RSCRIPT.is_file():
        rscript = DEFAULT_RSCRIPT.resolve()
    else:
        located = shutil.which("Rscript")
        if not located:
            raise RuntimeError("Rscript not found; install R >= 4.5.0 or set P2A_RSCRIPT")
        rscript = Path(located).resolve()
    if not rscript.is_file():
        raise RuntimeError(f"Rscript executable not found: {rscript}")
    cmd = [str(rscript), "--vanilla", str(R_SCRIPT), str(input_path), str(run_dir)]
    try:
        proc = subprocess.run(cmd, cwd=r_project, env=env, capture_output=True,
                              text=True, timeout=900, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("CausalImpact exceeded the 900-second timeout") from exc
    if proc.returncode:
        raise RuntimeError(f"CausalImpact R execution failed (exit {proc.returncode}):\n{(proc.stderr or proc.stdout)[-6000:]}")
    result_path = run_dir / "result.json"
    series_path = run_dir / "impact-series.csv"
    plot_path = run_dir / "impact-plot.pdf"
    if not all(p.is_file() and p.stat().st_size > 0 for p in (result_path, series_path, plot_path)):
        raise RuntimeError("CausalImpact completed but output artifacts are missing or empty")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["series"] = _read_csv(series_path)
    result["artifacts"] = [
        {"kind": "series_csv", "path": str(series_path.resolve())},
        {"kind": "impact_plot_pdf", "path": str(plot_path.resolve())},
    ]
    result["run_id"] = run_id
    return result
