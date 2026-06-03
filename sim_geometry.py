from __future__ import annotations

import math


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def distance(a: dict, b: dict) -> float:
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def local_to_world(point: dict, yaw_radians: float) -> dict:
    cosine = math.cos(yaw_radians)
    sine = math.sin(yaw_radians)
    return {
        "x": point["x"] * cosine - point["y"] * sine,
        "y": point["x"] * sine + point["y"] * cosine,
    }


def world_to_local(point: dict, center: dict, yaw_radians: float) -> dict:
    dx = point["x"] - center["x"]
    dy = point["y"] - center["y"]
    cosine = math.cos(-yaw_radians)
    sine = math.sin(-yaw_radians)
    return {
        "x": dx * cosine - dy * sine,
        "y": dx * sine + dy * cosine,
    }


def point_to_segment_distance(point: dict, a: dict, b: dict) -> float:
    dx = b["x"] - a["x"]
    dy = b["y"] - a["y"]
    if dx == 0 and dy == 0:
        return distance(point, a)
    t = ((point["x"] - a["x"]) * dx + (point["y"] - a["y"]) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    projected = {
        "x": a["x"] + dx * t,
        "y": a["y"] + dy * t,
    }
    return distance(point, projected)
