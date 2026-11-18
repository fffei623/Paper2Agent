"""Run a small, reproducible Scanpy workflow on the paper's PBMC 1k v3 data."""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import scanpy as sc


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "pbmc_1k_v3_filtered_feature_bc_matrix.h5"
RESULTS = ROOT / "results"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    sc.settings.figdir = RESULTS
    sc.settings.set_figure_params(dpi=120, facecolor="white")

    adata = sc.read_10x_h5(INPUT)
    adata.var_names_make_unique()
    input_shape = list(adata.shape)

    adata.var["mt"] = adata.var_names.str.startswith("MT-")
    sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
    sc.pp.filter_cells(adata, min_genes=100)
    sc.pp.filter_genes(adata, min_cells=3)
    filtered_shape = list(adata.shape)

    adata.raw = adata.copy()
    sc.pp.normalize_total(adata, target_sum=10_000)
    sc.pp.log1p(adata)
    sc.pp.highly_variable_genes(adata, n_top_genes=min(2000, adata.n_vars))
    adata = adata[:, adata.var.highly_variable].copy()
    sc.pp.scale(adata, max_value=10)
    sc.tl.pca(adata, svd_solver="arpack", random_state=0)
    sc.pp.neighbors(adata, n_neighbors=10, n_pcs=min(40, adata.obsm["X_pca"].shape[1]))
    sc.tl.umap(adata, random_state=0)
    sc.tl.leiden(
        adata,
        resolution=0.5,
        key_added="leiden",
        flavor="igraph",
        n_iterations=2,
        random_state=0,
    )

    output = RESULTS / "pbmc_1k_v3_scanpy.h5ad"
    adata.write_h5ad(output)
    sc.pl.umap(adata, color="leiden", show=False, save="_pbmc_1k_v3.png")

    summary = {
        "scanpy_version": version("scanpy"),
        "input_file": str(INPUT.relative_to(ROOT)),
        "input_shape_cells_genes": input_shape,
        "post_filter_shape_cells_genes": filtered_shape,
        "output_shape_cells_hvg": list(adata.shape),
        "parameters": {
            "min_genes_per_cell": 100,
            "min_cells_per_gene": 3,
            "normalization_target_sum": 10_000,
            "highly_variable_genes": min(2000, filtered_shape[1]),
            "neighbors": 10,
            "pca_components": min(40, adata.obsm["X_pca"].shape[1]),
            "leiden_resolution": 0.5,
            "random_state": 0,
        },
        "leiden_cluster_counts": {
            str(key): int(value)
            for key, value in adata.obs["leiden"].value_counts().sort_index().items()
        },
        "outputs": [output.name, "umap_pbmc_1k_v3.png"],
    }
    (RESULTS / "run-summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
