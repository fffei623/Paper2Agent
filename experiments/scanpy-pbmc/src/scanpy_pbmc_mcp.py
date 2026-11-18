"""FastMCP entry point for the reduced Scanpy PBMC workflow."""

from fastmcp import FastMCP

from tools.scanpy_workflow import scanpy_workflow_mcp

mcp = FastMCP(name="scanpy-pbmc")
mcp.mount(scanpy_workflow_mcp)


if __name__ == "__main__":
    mcp.run(transport="stdio")
