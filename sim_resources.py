from __future__ import annotations

import math
import random
from copy import deepcopy

from sim_geometry import clamp, distance, local_to_world, world_to_local


BASIN_MAX_CAPACITY = 100.0
BASIN_INITIAL_CAPACITY = 70.0
BASIN_LOW_THRESHOLD = 20.0
BASIN_REFILL_TARGET = 80.0
BASIN_REFILL_AMOUNT = 30.0
BASIN_DRINK_AMOUNT = 18.0
WATER_TRIP_LIMIT = 3

FIRE_COOK_SECONDS = 30.0
FOOD_EAT_AMOUNT = 35.0
FOOD_HUNGER_RESTORE = 45.0
WATER_THIRST_RESTORE = 45.0

PIGS_PER_FOREST = 6
PIG_RESPAWN_ATTEMPTS = 32
PIG_MOVE_SPEED_MIN = 80.0
PIG_MOVE_SPEED_MAX = 135.0
PIG_TURN_RATE = 2.4
PIG_DECISION_INTERVAL_MIN = 0.65
PIG_DECISION_INTERVAL_MAX = 2.0


def build_resource_state(layout: dict, rng: random.Random) -> dict:
    state = {
        "basins": {},
        "fires": {},
        "pigs": [],
        "nextPigIndex": 1,
    }
    sync_resource_state(layout, state, rng)
    return state


def sync_resource_state(layout: dict, state: dict, rng: random.Random) -> None:
    state.setdefault("basins", {})
    state.setdefault("fires", {})
    state.setdefault("pigs", [])
    state.setdefault("nextPigIndex", 1)

    basin_ids = set()
    fire_ids = set()
    for point in layout["points"]:
        if point["type"] == "Basin":
            basin_ids.add(point["id"])
            state["basins"].setdefault(
                point["id"],
                {
                    "pointId": point["id"],
                    "capacity": BASIN_INITIAL_CAPACITY,
                    "maximum": BASIN_MAX_CAPACITY,
                },
            )
        elif point["type"] == "Fire":
            fire_ids.add(point["id"])
            fire_state = state["fires"].setdefault(
                point["id"],
                {
                    "pointId": point["id"],
                    "slots": [],
                },
            )
            normalize_fire_slots(fire_state, max(1, int(point.get("slotCount", 1))))

    for point_id in list(state["basins"].keys()):
        if point_id not in basin_ids:
            del state["basins"][point_id]
    for point_id in list(state["fires"].keys()):
        if point_id not in fire_ids:
            del state["fires"][point_id]

    sync_forest_pigs(layout, state, rng)


def tick_resources(state: dict, dt: float, *, layout: dict | None = None, rng: random.Random | None = None) -> None:
    for fire_state in state.get("fires", {}).values():
        for slot in fire_state.get("slots", []):
            if slot["state"] != "raw":
                continue
            slot["cookRemaining"] = max(0.0, float(slot.get("cookRemaining", FIRE_COOK_SECONDS)) - dt)
            if slot["cookRemaining"] <= 0.0:
                slot["state"] = "cooked"
                slot["amount"] = max(1.0, float(slot.get("amount", 100.0)))
    if layout is not None and rng is not None:
        move_pigs(layout, state, dt, rng)


def normalize_fire_slots(fire_state: dict, slot_count: int) -> None:
    slots = fire_state.setdefault("slots", [])
    while len(slots) < slot_count:
        slots.append(empty_food_slot())
    while len(slots) > slot_count:
        slots.pop()
    if slots and all(slot.get("state") == "empty" for slot in slots):
        slots[0] = cooked_food_slot()
    for slot in slots:
        normalize_food_slot(slot)


def normalize_food_slot(slot: dict) -> None:
    state = slot.get("state", "empty")
    if state not in {"empty", "raw", "cooked"}:
        state = "empty"
    slot["state"] = state
    slot["amount"] = clamp(float(slot.get("amount", 0.0 if state == "empty" else 100.0)), 0.0, 100.0)
    slot["cookRemaining"] = clamp(float(slot.get("cookRemaining", FIRE_COOK_SECONDS if state == "raw" else 0.0)), 0.0, FIRE_COOK_SECONDS)
    if slot["amount"] <= 0.0:
        slot.update(empty_food_slot())


def empty_food_slot() -> dict:
    return {"state": "empty", "amount": 0.0, "cookRemaining": 0.0}


def raw_food_slot() -> dict:
    return {"state": "raw", "amount": 100.0, "cookRemaining": FIRE_COOK_SECONDS}


def cooked_food_slot() -> dict:
    return {"state": "cooked", "amount": 100.0, "cookRemaining": 0.0}


def basin_state(resources: dict, basin_id: str | None) -> dict | None:
    if basin_id is None:
        return None
    return resources.get("basins", {}).get(basin_id)


def fire_state(resources: dict, fire_id: str | None) -> dict | None:
    if fire_id is None:
        return None
    return resources.get("fires", {}).get(fire_id)


def basin_capacity_fraction(resources: dict, basin_id: str | None) -> float:
    basin = basin_state(resources, basin_id)
    if basin is None:
        return 0.0
    return clamp(float(basin.get("capacity", 0.0)) / max(1.0, float(basin.get("maximum", BASIN_MAX_CAPACITY))), 0.0, 1.0)


def drink_from_basin(resources: dict, basin_id: str | None, amount: float = BASIN_DRINK_AMOUNT) -> float:
    basin = basin_state(resources, basin_id)
    if basin is None:
        return 0.0
    available = max(0.0, float(basin.get("capacity", 0.0)))
    consumed = min(available, max(0.0, amount))
    basin["capacity"] = available - consumed
    return consumed


def fill_basin(resources: dict, basin_id: str | None, amount: float = BASIN_REFILL_AMOUNT) -> float:
    basin = basin_state(resources, basin_id)
    if basin is None:
        return 0.0
    maximum = max(1.0, float(basin.get("maximum", BASIN_MAX_CAPACITY)))
    before = clamp(float(basin.get("capacity", 0.0)), 0.0, maximum)
    after = clamp(before + max(0.0, amount), 0.0, maximum)
    basin["capacity"] = after
    return after - before


def is_basin_low(resources: dict, basin_id: str | None) -> bool:
    basin = basin_state(resources, basin_id)
    return basin is not None and float(basin.get("capacity", 0.0)) < BASIN_LOW_THRESHOLD


def is_basin_refilled(resources: dict, basin_id: str | None) -> bool:
    basin = basin_state(resources, basin_id)
    return basin is not None and float(basin.get("capacity", 0.0)) > BASIN_REFILL_TARGET


def fire_has_empty_slot(resources: dict, fire_id: str | None) -> bool:
    fire = fire_state(resources, fire_id)
    return fire is not None and any(slot["state"] == "empty" for slot in fire["slots"])


def fire_has_cooked_food(resources: dict, fire_id: str | None) -> bool:
    fire = fire_state(resources, fire_id)
    return fire is not None and any(slot["state"] == "cooked" and slot["amount"] > 0.0 for slot in fire["slots"])


def place_raw_pig(resources: dict, fire_id: str | None) -> bool:
    fire = fire_state(resources, fire_id)
    if fire is None:
        return False
    for index, slot in enumerate(fire["slots"]):
        if slot["state"] == "empty":
            fire["slots"][index] = raw_food_slot()
            return True
    return False


def eat_cooked_food(resources: dict, fire_id: str | None, amount: float = FOOD_EAT_AMOUNT) -> float:
    fire = fire_state(resources, fire_id)
    if fire is None:
        return 0.0
    for index, slot in enumerate(fire["slots"]):
        if slot["state"] != "cooked" or slot["amount"] <= 0.0:
            continue
        eaten = min(max(0.0, amount), float(slot["amount"]))
        slot["amount"] -= eaten
        if slot["amount"] <= 0.0:
            fire["slots"][index] = empty_food_slot()
        return eaten
    return 0.0


def point_by_id(layout: dict, point_id: str | None) -> dict | None:
    if point_id is None:
        return None
    for point in layout["points"]:
        if point["id"] == point_id:
            return point
    return None


def first_point(layout: dict, point_type: str, faction: str | None = None) -> dict | None:
    for point in layout["points"]:
        if point["type"] != point_type:
            continue
        if faction is not None and point["faction"] != faction:
            continue
        return point
    return None


def nearest_water_source_position(layout: dict, position: dict) -> dict | None:
    water_zones = [zone for zone in layout["zones"] if zone["type"] in {"Ocean", "Lake"}]
    if not water_zones:
        return None
    best_zone = min(water_zones, key=lambda zone: distance(position, closest_point_in_zone(position, zone)))
    return closest_point_in_zone(position, best_zone)


def closest_point_in_zone(point: dict, zone: dict) -> dict:
    local = world_to_local(point, zone["center"], zone["yawRadians"])
    half_x = zone["size"]["x"] * 0.5
    half_y = zone["size"]["y"] * 0.5
    clamped_local = {
        "x": clamp(local["x"], -half_x, half_x),
        "y": clamp(local["y"], -half_y, half_y),
    }
    rotated = local_to_world(clamped_local, zone["yawRadians"])
    return {
        "x": zone["center"]["x"] + rotated["x"],
        "y": zone["center"]["y"] + rotated["y"],
    }


def forest_zones(layout: dict) -> list[dict]:
    return [zone for zone in layout["zones"] if zone["type"] == "Forest"]


def north_forest(layout: dict) -> dict | None:
    for zone in layout["zones"]:
        if zone["type"] == "Forest" and "north" in zone["id"].lower():
            return zone
    forests = forest_zones(layout)
    if not forests:
        return None
    return min(forests, key=lambda zone: zone["center"]["y"])


def sync_forest_pigs(layout: dict, state: dict, rng: random.Random) -> None:
    forests = forest_zones(layout)
    forest_ids = {forest["id"] for forest in forests}
    state["pigs"] = [pig for pig in state.get("pigs", []) if pig.get("forestId") in forest_ids]
    for pig in state["pigs"]:
        normalize_pig_state(pig, rng)
    for forest in forests:
        while sum(1 for pig in state["pigs"] if pig["forestId"] == forest["id"]) < PIGS_PER_FOREST:
            state["pigs"].append(spawn_pig(layout, state, rng, forest, None))


def spawn_pig(layout: dict, state: dict, rng: random.Random, forest: dict, far_from: dict | None) -> dict:
    position = random_point_in_zone(forest, rng, margin=120.0)
    best = deepcopy(position)
    best_distance = -1.0
    for _ in range(PIG_RESPAWN_ATTEMPTS):
        candidate = random_point_in_zone(forest, rng, margin=120.0)
        score = distance(candidate, far_from) if far_from is not None else distance_to_nearest_pig(candidate, state)
        if score > best_distance:
            best = candidate
            best_distance = score
        if far_from is not None and score >= 1800.0:
            best = candidate
            break
    pig_id = f"pig-{state['nextPigIndex']}"
    state["nextPigIndex"] += 1
    return {
        "id": pig_id,
        "label": f"Pig {pig_id.split('-')[-1]}",
        "kind": "pig",
        "forestId": forest["id"],
        "position": best,
        "radius": 75.0,
        "headingRadians": rng.uniform(0.0, math.tau),
        "targetHeadingRadians": rng.uniform(0.0, math.tau),
        "moveSpeed": rng.uniform(PIG_MOVE_SPEED_MIN, PIG_MOVE_SPEED_MAX),
        "decisionTimer": rng.uniform(PIG_DECISION_INTERVAL_MIN, PIG_DECISION_INTERVAL_MAX),
    }


def normalize_pig_state(pig: dict, rng: random.Random) -> None:
    pig.setdefault("kind", "pig")
    pig.setdefault("radius", 75.0)
    pig.setdefault("headingRadians", rng.uniform(0.0, math.tau))
    pig.setdefault("targetHeadingRadians", pig["headingRadians"])
    pig.setdefault("moveSpeed", rng.uniform(PIG_MOVE_SPEED_MIN, PIG_MOVE_SPEED_MAX))
    pig.setdefault("decisionTimer", rng.uniform(PIG_DECISION_INTERVAL_MIN, PIG_DECISION_INTERVAL_MAX))


def move_pigs(layout: dict, state: dict, dt: float, rng: random.Random) -> None:
    forests_by_id = {forest["id"]: forest for forest in forest_zones(layout)}
    for pig in state.get("pigs", []):
        forest = forests_by_id.get(pig.get("forestId"))
        if forest is None:
            continue
        normalize_pig_state(pig, rng)
        pig["decisionTimer"] -= dt
        if pig["decisionTimer"] <= 0.0:
            pig["targetHeadingRadians"] = pig["headingRadians"] + rng.uniform(-1.4, 1.4)
            pig["decisionTimer"] = rng.uniform(PIG_DECISION_INTERVAL_MIN, PIG_DECISION_INTERVAL_MAX)
        pig["headingRadians"] = step_angle_towards(pig["headingRadians"], pig["targetHeadingRadians"], PIG_TURN_RATE * dt)
        proposed = {
            "x": pig["position"]["x"] + math.cos(pig["headingRadians"]) * pig["moveSpeed"] * dt,
            "y": pig["position"]["y"] + math.sin(pig["headingRadians"]) * pig["moveSpeed"] * dt,
        }
        clamped = closest_point_in_zone(proposed, forest)
        pig["position"] = clamped
        if distance(proposed, clamped) > 0.5:
            pig["targetHeadingRadians"] = rng.uniform(0.0, math.tau)
            pig["decisionTimer"] = rng.uniform(0.15, 0.45)


def step_angle_towards(current: float, target: float, max_delta: float) -> float:
    delta = math.atan2(math.sin(target - current), math.cos(target - current))
    if abs(delta) <= max_delta:
        return target
    return current + math.copysign(max_delta, delta)


def distance_to_nearest_pig(position: dict, state: dict) -> float:
    pigs = state.get("pigs", [])
    if not pigs:
        return 999999.0
    return min(distance(position, pig["position"]) for pig in pigs)


def random_point_in_zone(zone: dict, rng: random.Random, *, margin: float) -> dict:
    half_x = max(10.0, zone["size"]["x"] * 0.5 - margin)
    half_y = max(10.0, zone["size"]["y"] * 0.5 - margin)
    local = {
        "x": rng.uniform(-half_x, half_x),
        "y": rng.uniform(-half_y, half_y),
    }
    rotated = local_to_world(local, zone["yawRadians"])
    return {
        "x": zone["center"]["x"] + rotated["x"],
        "y": zone["center"]["y"] + rotated["y"],
    }


def nearest_north_forest_pig(layout: dict, state: dict, position: dict) -> dict | None:
    forest = north_forest(layout)
    if forest is None:
        return None
    pigs = [pig for pig in state.get("pigs", []) if pig["forestId"] == forest["id"]]
    if not pigs:
        return None
    return min(pigs, key=lambda pig: distance(position, pig["position"]))


def nearest_attack_target(layout: dict, state: dict, position: dict, target_filter: dict) -> dict | None:
    if target_filter.get("kind") == "pig":
        if target_filter.get("forest") == "north":
            return nearest_north_forest_pig(layout, state, position)
        pigs = state.get("pigs", [])
        if not pigs:
            return None
        return min(pigs, key=lambda pig: distance(position, pig["position"]))
    return None


def attack_target_by_ref(layout: dict, state: dict, target_ref: dict | None) -> dict | None:
    if not isinstance(target_ref, dict):
        return None
    if target_ref.get("kind") == "pig":
        return next((pig for pig in state.get("pigs", []) if pig["id"] == target_ref.get("id")), None)
    return None


def attack_target_ref(target: dict) -> dict:
    return {
        "kind": target.get("kind", "unknown"),
        "id": target["id"],
        "label": target.get("label", target["id"]),
        "radius": float(target.get("radius", 75.0)),
    }


def defeat_attack_target(layout: dict, state: dict, target_ref: dict, rng: random.Random) -> dict | None:
    if target_ref.get("kind") == "pig":
        return kill_and_respawn_pig(layout, state, target_ref.get("id"), rng)
    return None


def kill_and_respawn_pig(layout: dict, state: dict, pig_id: str, rng: random.Random) -> dict | None:
    for index, pig in enumerate(state.get("pigs", [])):
        if pig["id"] != pig_id:
            continue
        killed_position = deepcopy(pig["position"])
        forest = next((zone for zone in layout["zones"] if zone["id"] == pig["forestId"]), None)
        state["pigs"].pop(index)
        if forest is not None:
            state["pigs"].append(spawn_pig(layout, state, rng, forest, killed_position))
        return pig
    return None
