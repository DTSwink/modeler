from __future__ import annotations

import math
import random
from copy import deepcopy


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


def format_sim_time(seconds: float) -> str:
    total_seconds = max(0.0, float(seconds))
    minutes = int(total_seconds // 60.0)
    remainder = total_seconds - minutes * 60.0
    return f"{minutes:02d}:{remainder:04.1f}"


def format_speed_label(multiplier: float) -> str:
    if abs(multiplier - round(multiplier)) < 0.001:
        return f"{int(round(multiplier))}x"
    return f"{multiplier:g}x"


class RomanSimulationRuntime:
    def __init__(
        self,
        layout: dict,
        *,
        spawn_zone_id: str,
        agent_count: int,
        rng_seed: int = 1337,
    ) -> None:
        self._layout = layout
        self.spawn_zone_id = spawn_zone_id
        self.agent_count = agent_count
        self.rng = random.Random(rng_seed)
        self.running = False
        self.speed_multiplier = 1.0
        self.time_seconds = 0.0
        self.agents = self._build_initial_agents(rng_seed)

    def attach_layout(self, layout: dict) -> None:
        self._layout = layout
        self.clamp_all_agents_to_bounds()

    def world_dimensions(self) -> tuple[float, float]:
        return (
            max(1.0, float(self._layout["root"]["gridSize"]["x"] * self._layout["root"]["cellSize"])),
            max(1.0, float(self._layout["root"]["gridSize"]["y"] * self._layout["root"]["cellSize"])),
        )

    def spawn_zone(self) -> dict:
        for zone in self._layout["zones"]:
            if zone["id"] == self.spawn_zone_id:
                return zone
        for zone in self._layout["zones"]:
            if zone["type"] == "Camp" and zone["faction"] == "Roman":
                return zone
        world_width, world_height = self.world_dimensions()
        return {
            "center": {"x": world_width * 0.5, "y": world_height * 0.5},
            "size": {"x": world_width, "y": world_height},
            "yawRadians": 0.0,
        }

    def summary_text(self, *, freeze_layout: bool) -> str:
        state_text = "Running" if self.running else "Paused"
        freeze_suffix = " | Layout frozen" if freeze_layout else ""
        return f"{state_text} | Sim {format_sim_time(self.time_seconds)} | {len(self.agents)} Roman agents | {format_speed_label(self.speed_multiplier)}{freeze_suffix}"

    def get_agent_by_id(self, agent_id: str | None) -> dict | None:
        if agent_id is None:
            return None
        for agent in self.agents:
            if agent["id"] == agent_id:
                return agent
        return None

    def clamp_agent_position(self, agent: dict, position: dict) -> tuple[dict, bool, bool]:
        world_width, world_height = self.world_dimensions()
        margin = max(110.0, agent["radius"] * 1.2)
        max_x = max(margin, world_width - margin)
        max_y = max(margin, world_height - margin)
        clamped_position = {
            "x": clamp(position["x"], margin, max_x),
            "y": clamp(position["y"], margin, max_y),
        }
        hit_x = abs(clamped_position["x"] - position["x"]) > 0.001
        hit_y = abs(clamped_position["y"] - position["y"]) > 0.001
        return (clamped_position, hit_x, hit_y)

    def clamp_all_agents_to_bounds(self) -> None:
        for agent in self.agents:
            clamped_position, _, _ = self.clamp_agent_position(agent, agent["position"])
            agent["position"] = clamped_position

    def advance(self, sim_dt: float, *, dragged_agent_id: str | None = None) -> bool:
        if sim_dt <= 0.0:
            return False
        any_changed = False
        self.time_seconds += sim_dt
        for agent in self.agents:
            if dragged_agent_id == agent["id"]:
                continue
            agent["decisionTimer"] -= sim_dt
            if agent["decisionTimer"] <= 0.0:
                agent["targetHeadingRadians"] = agent["headingRadians"] + self.rng.uniform(-1.7, 1.7)
                agent["decisionTimer"] = self.rng.uniform(0.35, 1.4)
            agent["headingRadians"] = self._step_angle_towards(
                agent["headingRadians"],
                agent["targetHeadingRadians"],
                agent["turnRate"] * sim_dt,
            )
            proposed = {
                "x": agent["position"]["x"] + math.cos(agent["headingRadians"]) * agent["moveSpeed"] * sim_dt,
                "y": agent["position"]["y"] + math.sin(agent["headingRadians"]) * agent["moveSpeed"] * sim_dt,
            }
            clamped, hit_x, hit_y = self.clamp_agent_position(agent, proposed)
            agent["position"] = clamped
            if hit_x or hit_y:
                agent["targetHeadingRadians"] = self.rng.uniform(0.0, math.tau)
                agent["decisionTimer"] = self.rng.uniform(0.12, 0.35)
            any_changed = True
        return any_changed

    def _build_initial_agents(self, rng_seed: int) -> list[dict]:
        zone = self.spawn_zone()
        rng = random.Random(rng_seed)
        agents: list[dict] = []
        for index in range(self.agent_count):
            position = self._random_point_in_zone(zone, rng, agents)
            heading = rng.uniform(0.0, math.tau)
            agents.append(
                {
                    "id": f"agent-roman-{index + 1}",
                    "label": f"Roman Agent {index + 1}",
                    "faction": "Roman",
                    "position": position,
                    "radius": 90.0,
                    "headingRadians": heading,
                    "targetHeadingRadians": heading,
                    "moveSpeed": rng.uniform(145.0, 225.0),
                    "turnRate": rng.uniform(1.4, 2.5),
                    "decisionTimer": rng.uniform(0.35, 1.6),
                }
            )
        return agents

    def _random_point_in_zone(self, zone: dict, rng: random.Random, existing_agents: list[dict] | None = None) -> dict:
        margin = 180.0
        half_x = max(140.0, zone["size"]["x"] * 0.5 - margin)
        half_y = max(140.0, zone["size"]["y"] * 0.5 - margin)
        best_point = deepcopy(zone["center"])
        for _ in range(16):
            local = {
                "x": rng.uniform(-half_x, half_x),
                "y": rng.uniform(-half_y, half_y),
            }
            rotated = local_to_world(local, zone["yawRadians"])
            candidate = {
                "x": zone["center"]["x"] + rotated["x"],
                "y": zone["center"]["y"] + rotated["y"],
            }
            if not existing_agents:
                return candidate
            if all(distance(candidate, agent["position"]) >= 220.0 for agent in existing_agents):
                return candidate
            best_point = candidate
        return best_point

    def _wrap_angle(self, angle_radians: float) -> float:
        return math.atan2(math.sin(angle_radians), math.cos(angle_radians))

    def _step_angle_towards(self, current: float, target: float, max_delta: float) -> float:
        delta = self._wrap_angle(target - current)
        if abs(delta) <= max_delta:
            return target
        return current + math.copysign(max_delta, delta)
