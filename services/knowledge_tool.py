from __future__ import annotations

from pathlib import Path

from google.adk.tools.function_tool import FunctionTool


KNOWLEDGE_FILE = (
    Path(__file__).resolve().parents[1] / "app" / "knowledge" / "mg_cafe.md"
)


def _get_mg_cafe_knowledge() -> dict:
    """
    Return the MG Cafe ground-truth knowledge file as plain text.
    """
    if not KNOWLEDGE_FILE.exists():
        return {"text": "", "error": f"Knowledge file not found: {KNOWLEDGE_FILE}"}
    return {"text": KNOWLEDGE_FILE.read_text(encoding="utf-8")}


get_mg_cafe_knowledge = FunctionTool(_get_mg_cafe_knowledge)
