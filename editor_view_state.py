from __future__ import annotations

from sim_geometry import clamp


def normalize_saved_view(layout: dict) -> None:
    default_center = {
        "x": float(layout["root"]["gridSize"]["x"] * layout["root"]["cellSize"]) * 0.5,
        "y": float(layout["root"]["gridSize"]["y"] * layout["root"]["cellSize"]) * 0.5,
    }
    saved_view = layout["editor"].setdefault("savedView", {})
    saved_view["zoom"] = clamp(float(saved_view.get("zoom", 1.0)), 0.35, 8.0)
    saved_center = saved_view.setdefault("center", default_center)
    if not isinstance(saved_center, dict):
        saved_center = default_center
        saved_view["center"] = saved_center
    saved_center["x"] = float(saved_center.get("x", default_center["x"]))
    saved_center["y"] = float(saved_center.get("y", default_center["y"]))


def read_saved_view(layout: dict, fallback_center: dict) -> tuple[float, dict]:
    saved_view = layout.get("editor", {}).get("savedView", {})
    saved_center = saved_view.get("center", fallback_center)
    if not isinstance(saved_center, dict):
        saved_center = fallback_center
    return (
        clamp(float(saved_view.get("zoom", 1.0)), 0.35, 8.0),
        {
            "x": float(saved_center.get("x", fallback_center["x"])),
            "y": float(saved_center.get("y", fallback_center["y"])),
        },
    )


def write_saved_view(layout: dict, zoom: float, center: dict) -> None:
    layout.setdefault("editor", {})
    layout["editor"]["savedView"] = {
        "zoom": round(float(zoom), 4),
        "center": {
            "x": round(float(center["x"]), 2),
            "y": round(float(center["y"]), 2),
        },
    }
