"""Renders previews with the same renderer the official pipeline uses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "brand_kit" / "assets"


def render_preview(design: dict[str, Any], png_path: Path) -> list[str]:
    """Render ``design`` to ``png_path``; return the renderer's warnings."""
    from renderer.converter.convert import render_design_to_png

    return list(render_design_to_png(design, ASSETS_DIR, png_path) or [])


def renderer_available() -> bool:
    try:
        import renderer.converter.convert  # noqa: F401
    except Exception:  # noqa: BLE001 - any import failure means no previews
        return False
    return True
