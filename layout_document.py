from __future__ import annotations

import json
from pathlib import Path

from editor_view_state import normalize_saved_view


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def deep_copy(payload: dict) -> dict:
    return json.loads(json.dumps(payload))


def merge_layout_save(base, current, disk):
    if isinstance(current, dict):
        result = deep_copy(disk) if isinstance(disk, dict) else {}
        base_dict = base if isinstance(base, dict) else {}
        disk_dict = disk if isinstance(disk, dict) else {}
        for key, current_value in current.items():
            if key not in base_dict:
                result[key] = deep_copy(current_value)
                continue
            if current_value == base_dict[key]:
                if key not in result:
                    result[key] = deep_copy(current_value)
                continue
            result[key] = merge_layout_save(base_dict[key], current_value, disk_dict.get(key))
        return result

    if isinstance(current, list):
        return _merge_layout_list_save(base, current, disk)

    if current == base:
        return deep_copy(disk) if disk is not None else deep_copy(current)
    return deep_copy(current)


def _merge_layout_list_save(base, current, disk):
    if not _is_id_list(current):
        if current == base:
            return deep_copy(disk) if isinstance(disk, list) else deep_copy(current)
        return deep_copy(current)

    current_ids = {
        item["id"]
        for item in current
        if isinstance(item, dict) and "id" in item
    }
    base_by_id = {
        item["id"]: item
        for item in base
        if isinstance(item, dict) and "id" in item
    } if isinstance(base, list) else {}
    disk_items = deep_copy(disk) if isinstance(disk, list) else []
    disk_by_id = {
        item["id"]: index
        for index, item in enumerate(disk_items)
        if isinstance(item, dict) and "id" in item
    }

    for current_item in current:
        if not isinstance(current_item, dict) or "id" not in current_item:
            continue
        item_id = current_item["id"]
        if item_id in base_by_id:
            if item_id in disk_by_id:
                index = disk_by_id[item_id]
                disk_items[index] = merge_layout_save(base_by_id[item_id], current_item, disk_items[index])
            else:
                disk_by_id[item_id] = len(disk_items)
                disk_items.append(deep_copy(current_item))
        elif item_id in disk_by_id:
            disk_items[disk_by_id[item_id]] = deep_copy(current_item)
        else:
            disk_by_id[item_id] = len(disk_items)
            disk_items.append(deep_copy(current_item))

    removed_ids = set(base_by_id) - current_ids
    if removed_ids:
        disk_items = [
            item
            for item in disk_items
            if not (isinstance(item, dict) and item.get("id") in removed_ids)
        ]
    return disk_items


def _is_id_list(value) -> bool:
    return isinstance(value, list) and any(isinstance(item, dict) and "id" in item for item in value)


def normalize_layout(payload: dict, *, zone_color_resolver, updated_default: str) -> dict:
    layout = deep_copy(payload)
    layout.setdefault("editor", {})
    layout["editor"].setdefault("snapToGrid", True)
    layout["editor"].setdefault("snapSize", 50)
    layout["editor"].setdefault("labelFontSize", 12)
    layout["editor"].setdefault("labelMode", "Hover")
    layout.setdefault("root", {})
    layout["root"].setdefault("cellSize", 100)
    layout["root"].setdefault("gridSize", {"x": 240, "y": 80})
    layout["root"].setdefault("drawLayout", True)
    layout["root"].setdefault("drawGrid", True)
    layout["root"].setdefault("drawLabels", True)
    layout.setdefault("zones", [])
    if "points" not in layout and "locations" in layout:
        layout["points"] = layout["locations"]
    layout.setdefault("points", [])
    layout["locations"] = layout["points"]
    layout.setdefault("walls", [])
    layout.setdefault("summary", "Editable layout marker foundation.")
    layout.setdefault("footer", "Native local editor for the latest Modeler layout state.")
    layout.setdefault("stage", "Engine-independent layout editor")
    layout.setdefault("block", "0A")
    layout.setdefault("updated", updated_default)
    normalize_saved_view(layout)

    for index, zone in enumerate(layout["zones"]):
        zone.setdefault("id", f"zone-{index + 1}")
        zone.setdefault("label", zone["id"])
        zone.setdefault("type", "Walkable")
        zone.setdefault("faction", "Neutral")
        zone.setdefault("color", "#bca278")
        zone.setdefault("priority", 0)
        zone.setdefault("yawRadians", 0.0)
        zone.setdefault("center", {"x": 0.0, "y": 0.0})
        zone.setdefault("size", {"x": 1000.0, "y": 1000.0})
        zone["color"] = zone_color_resolver(zone["type"], zone["color"])

    for index, point in enumerate(layout["points"]):
        point.setdefault("id", f"point-{index + 1}")
        point.setdefault("label", point["id"])
        point.setdefault("type", "RallyPoint")
        point.setdefault("faction", "Neutral")
        point.setdefault("slotCount", 1)
        point.setdefault("facingRadians", 0.0)
        point.setdefault("radius", 100.0)
        point.setdefault("position", {"x": 0.0, "y": 0.0})

    for index, wall in enumerate(layout["walls"]):
        wall.setdefault("id", f"wall-{index + 1}")
        wall.setdefault("faction", "Neutral")
        wall.setdefault("thickness", 100.0)
        wall.setdefault("a", {"x": 0.0, "y": 0.0})
        wall.setdefault("b", {"x": 1000.0, "y": 0.0})

    return layout
