# Scanpy PBMC MCP

## Scope

This server exposes one workflow for preprocessing and clustering a single 10x Genomics filtered feature-barcode HDF5 matrix with Scanpy. It is a reduced workflow for learning and validation, not the paper's full seven-dataset evaluation. CPU execution is supported; GPU is not required.

## Runtime and installation

Requires Python 3.14.7. Install dependencies from this directory with `python -m pip install -r requirements.txt` (or use uv). Scanpy is pinned to commit `3962176e93ba148bc0f61443c517877d736f2b3b`.

## Start

From the `src/` directory run:

```powershell
python scanpy_pbmc_mcp.py
```

The server uses MCP stdio transport. Configure the MCP client to launch the Python interpreter with `scanpy_pbmc_mcp.py` as its script argument.

## Tool

`preprocess_and_cluster_10x` requires `input_h5` (path to a 10x HDF5 matrix) and `output_dir` (base output directory). Optional parameters are `min_genes` (100), `min_cells` (3), `n_top_genes` (2000), `n_neighbors` (10), `resolution` (0.5), and `random_state` (0). It returns matrix shapes, Leiden cluster counts, and paths to a clustered `.h5ad`, UMAP PNG, and JSON summary. Each call writes to a unique subdirectory under `output_dir`.

## Validation limits

Validated on PBMC 1k v3: the H5AD cell/gene identifiers, expression matrix, and Leiden labels matched an independent upstream Scanpy API run. MCP stdio checks covered tool inventory/schema, successful and repeated calls, changed HVG count, and missing input. Clean-runtime installation and relocated ZIP validation are pending. A 10x HDF5 input must be supplied by the user; no dataset is bundled.
