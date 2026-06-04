from __future__ import annotations

import math

from sim_geometry import distance


VISION_DISTANCE = 1500.0
VISION_HALF_ANGLE_RADIANS = math.radians(38.0)


def angle_delta(a: float, b: float) -> float:
    return math.atan2(math.sin(a - b), math.cos(a - b))


def is_in_vision_cone(agent: dict, target_position: dict) -> bool:
    dx = target_position["x"] - agent["position"]["x"]
    dy = target_position["y"] - agent["position"]["y"]
    target_distance = math.hypot(dx, dy)
    if target_distance > VISION_DISTANCE:
        return False
    if target_distance <= max(1.0, float(agent.get("radius", 90.0))):
        return True
    target_angle = math.atan2(dy, dx)
    heading = float(agent.get("headingRadians", 0.0))
    return abs(angle_delta(target_angle, heading)) <= VISION_HALF_ANGLE_RADIANS


def nearest_visible_dead_pig(agent: dict, resources: dict) -> dict | None:
    visible = [
        dead_pig
        for dead_pig in resources.get("deadPigs", [])
        if is_in_vision_cone(agent, dead_pig["position"])
    ]
    if not visible:
        return None
    return min(visible, key=lambda dead_pig: distance(agent["position"], dead_pig["position"]))


def visible_dead_pig_carriers(observer: dict, agents: list[dict]) -> list[dict]:
    visible = []
    observer_id = observer.get("id")
    for agent in agents:
        if agent.get("id") == observer_id:
            continue
        if agent.get("health", {}).get("status") == "dead":
            continue
        if not agent.get("inventory", {}).get("rawPig"):
            continue
        if is_in_vision_cone(observer, agent["position"]):
            visible.append(agent)
    return visible


def vision_cone_points(agent: dict, *, segments: int = 12) -> list[dict]:
    origin = agent["position"]
    heading = float(agent.get("headingRadians", 0.0))
    points = [origin]
    for index in range(max(1, segments) + 1):
        angle = heading - VISION_HALF_ANGLE_RADIANS + 2.0 * VISION_HALF_ANGLE_RADIANS * index / max(1, segments)
        points.append(
            {
                "x": origin["x"] + math.cos(angle) * VISION_DISTANCE,
                "y": origin["y"] + math.sin(angle) * VISION_DISTANCE,
            }
        )
    return points
