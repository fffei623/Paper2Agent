"""MCP wrapper around the Scanpy preprocessing and clustering APIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import matplotlib
matplotlib.use("Agg")
import scanpy as sc
from fastmcp import FastMCP

scanpy_workflow_mcp = FastMCP(name="scanpy_workflow")
REFERENCE = (
    "https://github.com/scverse/scanpy/blob/3962176e93ba148bc0f61443c517877d736f2b3b/"
    "docs/tutorials/basics/clustering.ipynb"
)


@scanpy_workflow_mcp.tool()
def preprocess_and_cluster_10x(
    input_h5: Annotated[str, "Path to a 10x Genomics filtered feature-barcode HDF5 matrix"],
    output_dir: Annotated[str, "Directory where the H5AD, UMAP image, and summary will be written"],
    min_genes: Annotated[int, "Minimum genes detected per cell; Scanpy filter_cells parameter"] = 100,
    min_cells: Annotated[int, "Minimum cells expressing each gene; Scanpy filter_genes parameter"] = 3,
    n_top_genes: Annotated[int, "Maximum number of highly variable genes to retain"] = 2000,
    n_neighbors: Annotated[int, "Number of neighbors used to construct the cell graph"] = 10,
    resolution: Annotated[float, "Leiden clustering resolution"] = 0.5,
    random_state: Annotated[int, "Seed passed to Scanpy PCA, UMAP, and Leiden"] = 0,
) -> dict:
    """Run Scanpy quality control, preprocessing, and clustering.
    Input is a 10x HDF5 matrix; output is a clustered H5AD, UMAP figure, and run summary.
    """
    source = Path(input_h5).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    if source.suffix.lower() != ".h5":
        raise ValueError("input_h5 must be a .h5 10x matrix")
    if min_genes < 1 or min_cells < 1 or n_top_genes < 2 or n_neighbors < 2:
        raise ValueError("min_genes/min_cells must be positive; n_top_genes/n_neighbors must be at least 2")
    if resolution <= 0:
        raise ValueError("resolution must be greater than zero")

    output_root = Path(output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    destination = output_root / f"run_{uuid4().hex}"
    destination.mkdir()
    adata = sc.read_10x_h5(source)
    adata.var_names_make_unique()
    input_shape = list(adata.shape)
    if adata.n_obs == 0 or adata.n_vars == 0:
        raise ValueError("Input matrix has no cells or genes")

    adata.var["mt"] = adata.var_names.str.startswith("MT-")
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
    sc.pp.filter_cells(adata, min_genes=min_genes)
    sc.pp.filter_genes(adata, min_cells=min_cells)
    if adata.n_obs < 3 or adata.n_vars < 2:
        raise ValueError("QC filtering left too few cells or genes for PCA and clustering")
    filtered_shape = list(adata.shape)

    adata.raw = adata.copy()
    sc.pp.normalize_total(adata, target_sum=10_000)
    sc.pp.log1p(adata)
    n_hvg = min(n_top_genes, adata.n_vars)
    sc.pp.highly_variable_genes(adata, n_top_genes=n_hvg)
    adata = adata[:, adata.var.highly_variable].copy()
    sc.pp.scale(adata, max_value=10)
    sc.tl.pca(adata, svd_solver="arpack", random_state=random_state)
    n_pcs = min(40, adata.obsm["X_pca"].shape[1])
    actual_neighbors = min(n_neighbors, adata.n_obs - 1)
    sc.pp.neighbors(adata, n_neighbors=actual_neighbors, n_pcs=n_pcs)
    sc.tl.umap(adata, random_state=random_state)
    sc.tl.leiden(
        adata, resolution=resolution, key_added="leiden", flavor="igraph",
        n_iterations=2, random_state=random_state,
    )

    h5ad_path = destination / "scanpy_clustered.h5ad"
    figure_path = destination / "umap_leiden.png"
    summary_path = destination / "summary.json"
    adata.write_h5ad(h5ad_path)
    sc.settings.figdir = destination
    sc.settings.set_figure_params(dpi=120, facecolor="white")
    sc.pl.umap(adata, color="leiden", show=False, save="_leiden.png")
    summary = {
        "input_shape_cells_genes": input_shape,
        "post_filter_shape_cells_genes": filtered_shape,
        "output_shape_cells_hvg": list(adata.shape),
        "parameters": {
            "min_genes": min_genes, "min_cells": min_cells,
            "n_top_genes": n_hvg, "normalization_target_sum": 10000,
            "n_neighbors": actual_neighbors, "n_pcs": n_pcs,
            "resolution": resolution, "random_state": random_state,
        },
        "leiden_cluster_counts": {
            str(k): int(v) for k, v in adata.obs["leiden"].value_counts().sort_index().items()
        },
        "artifacts": [
            {"description": "Clustered AnnData result", "path": str(h5ad_path.resolve())},
            {"description": "UMAP plot colored by Leiden clusters", "path": str(figure_path.resolve())},
            {"description": "Run parameters and cluster counts", "path": str(summary_path.resolve())},
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {
        "message": "Scanpy preprocessing and Leiden clustering completed.",
        "reference": REFERENCE,
        **summary,
    }
