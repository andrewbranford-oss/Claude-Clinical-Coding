"""MCP server for the NHS clinical coding workspace."""

from __future__ import annotations

from fastmcp import FastMCP

from classbrowser_tool import search_classbrowser


mcp = FastMCP(
    "NHS Clinical Coding",
    instructions=(
        "Tools for NHS clinical coding workflows, including live lookups "
        "against the NHS Classifications Browser."
    ),
)


@mcp.tool
def search_nhs_classbrowser(search_term: str, classification: str) -> str:
    """Search ICD-10 or OPCS-4 in the NHS Classifications Browser."""
    return search_classbrowser(search_term=search_term, classification=classification)


if __name__ == "__main__":
    mcp.run()
