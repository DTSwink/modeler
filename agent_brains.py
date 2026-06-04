from __future__ import annotations

import math
import random

import sim_resources
from sim_geometry import clamp, distance


HUNGER_DEPLETION_PER_SECOND = 0.34
THIRST_DEPLETION_PER_SECOND = 0.52
NEED_CHECK_INTERVAL_MIN = 0.45
NEED_CHECK_INTERVAL_MAX = 1.15
ARRIVAL_EXTRA_MARGIN = 90.0


def normalize_brain_state(agent: dict) -> None:
    agent.setdefault("brain", "NeedsWorker")
    agent.setdefault("intent", {"action": "wander", "reason": "initializing"})
    agent.setdefault("job", None)
    inventory = agent.get("inventory") if isinstance(agent.get("inventory"), dict) else {}
    inventory.setdefault("jar", False)
    inventory.setdefault("jarFilled", False)
    inventory.setdefault("rawPig", False)
    agent["inventory"] = inventory
    agent.setdefault("needCheckTimer", 0.0)


def deplete_needs(agent: dict, dt: float) -> None:
    normalize_brain_state(agent)
    if agent["health"]["status"] == "dead":
        return
    agent["needs"]["hunger"] = max(0, agent["needs"]["hunger"] - HUNGER_DEPLETION_PER_SECOND * dt)
    agent["needs"]["thirst"] = max(0, agent["needs"]["thirst"] - THIRST_DEPLETION_PER_SECOND * dt)
    if agent["needs"]["hunger"] <= 0 or agent["needs"]["thirst"] <= 0:
        agent["health"]["status"] = "dead"
        agent["job"] = None
        agent["intent"] = {"action": "dead", "reason": "needs reached zero"}


def advance_agent(agent: dict, dt: float, context: dict) -> bool:
    normalize_brain_state(agent)
    if agent["health"]["status"] == "dead":
        agent["intent"] = {"action": "dead", "reason": "dead agents do not decide"}
        return False

    if agent.get("job") is not None:
        return advance_job(agent, dt, context)

    maybe_assign_job(agent, context)
    if agent.get("job") is not None:
        return advance_job(agent, dt, context)

    return wander(agent, dt, context)


def maybe_assign_job(agent: dict, context: dict) -> None:
    layout = context["layout"]
    resources = context["resources"]
    rng = context["rng"]
    faction = agent["faction"]
    basin = sim_resources.first_point(layout, "Basin", faction)
    fire = sim_resources.first_point(layout, "Fire", faction)

    thirst = float(agent["needs"]["thirst"])
    hunger = float(agent["needs"]["hunger"])
    agent["needCheckTimer"] -= context["dt"]
    check_now = agent["needCheckTimer"] <= 0.0
    if check_now:
        agent["needCheckTimer"] = rng.uniform(NEED_CHECK_INTERVAL_MIN, NEED_CHECK_INTERVAL_MAX)

    if basin and sim_resources.is_basin_low(resources, basin["id"]):
        if thirst < 95.0 and sim_resources.basin_state(resources, basin["id"])["capacity"] > 0:
            assign_drink_job(agent, basin, "basin low; drink before refilling")
        else:
            assign_water_job(agent, layout, basin)
        return

    if fire and sim_resources.fire_has_empty_slot(resources, fire["id"]):
        if hunger < 95.0 and sim_resources.fire_has_cooked_food(resources, fire["id"]):
            assign_eat_job(agent, fire, "empty fire slot noticed; eat before hunting")
        else:
            assign_hunt_job(agent, layout, resources, rng, fire)
        return

    if not check_now:
        return

    if basin and should_satisfy_need(thirst, rng) and sim_resources.basin_state(resources, basin["id"])["capacity"] > 0:
        assign_drink_job(agent, basin, "thirst probability check")
        return

    if fire and should_satisfy_need(hunger, rng) and sim_resources.fire_has_cooked_food(resources, fire["id"]):
        assign_eat_job(agent, fire, "hunger probability check")


def should_satisfy_need(value: float, rng: random.Random) -> bool:
    if value <= 35.0:
        return True
    pressure = clamp((100.0 - value) / 100.0, 0.0, 1.0)
    return rng.random() < pressure * pressure


def assign_drink_job(agent: dict, basin: dict, reason: str) -> None:
    agent["job"] = {
        "type": "drink",
        "basinId": basin["id"],
    }
    agent["intent"] = {"action": "go_to", "target": basin["label"], "reason": reason}


def assign_eat_job(agent: dict, fire: dict, reason: str) -> None:
    agent["job"] = {
        "type": "eat",
        "fireId": fire["id"],
    }
    agent["intent"] = {"action": "go_to", "target": fire["label"], "reason": reason}


def assign_water_job(agent: dict, layout: dict, basin: dict) -> None:
    jar_location = sim_resources.first_point(layout, "JarLocation", agent["faction"])
    water_position = sim_resources.nearest_water_source_position(layout, basin["position"])
    agent["job"] = {
        "type": "fetch_water",
        "phase": "to_jar" if jar_location else "to_water",
        "basinId": basin["id"],
        "jarLocationId": jar_location["id"] if jar_location else None,
        "waterPosition": water_position,
        "trips": 0,
    }
    agent["intent"] = {"action": "go_to", "target": jar_location["label"] if jar_location else "Water", "reason": "basin below 20%"}


def assign_hunt_job(agent: dict, layout: dict, resources: dict, rng: random.Random, fire: dict) -> None:
    pig = sim_resources.nearest_north_forest_pig(layout, resources, agent["position"])
    if pig is None:
        agent["intent"] = {"action": "wander", "reason": "no north forest pig available"}
        return
    agent["job"] = {
        "type": "hunt_pig",
        "phase": "to_pig",
        "fireId": fire["id"],
        "pigId": pig["id"],
    }
    agent["intent"] = {"action": "go_to", "target": pig["label"], "reason": "fire has an empty slot"}


def advance_job(agent: dict, dt: float, context: dict) -> bool:
    job_type = agent["job"].get("type")
    if job_type == "drink":
        return advance_drink_job(agent, dt, context)
    if job_type == "eat":
        return advance_eat_job(agent, dt, context)
    if job_type == "fetch_water":
        return advance_water_job(agent, dt, context)
    if job_type == "hunt_pig":
        return advance_hunt_job(agent, dt, context)
    agent["job"] = None
    return False


def advance_drink_job(agent: dict, dt: float, context: dict) -> bool:
    basin = sim_resources.point_by_id(context["layout"], agent["job"].get("basinId"))
    if basin is None:
        agent["job"] = None
        return False
    if not at_point(agent, basin):
        agent["intent"] = {"action": "go_to", "target": basin["label"], "reason": "drink from basin"}
        return move_towards(agent, basin["position"], dt, context)
    consumed = sim_resources.drink_from_basin(context["resources"], basin["id"])
    if consumed > 0.0:
        agent["needs"]["thirst"] = clamp(agent["needs"]["thirst"] + sim_resources.WATER_THIRST_RESTORE, 0.0, 100.0)
    if sim_resources.is_basin_low(context["resources"], basin["id"]):
        assign_water_job(agent, context["layout"], basin)
    else:
        finish_job(agent, "drank from basin")
    return True


def advance_eat_job(agent: dict, dt: float, context: dict) -> bool:
    fire = sim_resources.point_by_id(context["layout"], agent["job"].get("fireId"))
    if fire is None:
        agent["job"] = None
        return False
    if not at_point(agent, fire):
        agent["intent"] = {"action": "go_to", "target": fire["label"], "reason": "eat cooked pig"}
        return move_towards(agent, fire["position"], dt, context)
    eaten = sim_resources.eat_cooked_food(context["resources"], fire["id"])
    if eaten > 0.0:
        agent["needs"]["hunger"] = clamp(agent["needs"]["hunger"] + sim_resources.FOOD_HUNGER_RESTORE, 0.0, 100.0)
    if sim_resources.fire_has_empty_slot(context["resources"], fire["id"]):
        assign_hunt_job(agent, context["layout"], context["resources"], context["rng"], fire)
    else:
        finish_job(agent, "ate cooked pig")
    return True


def advance_water_job(agent: dict, dt: float, context: dict) -> bool:
    layout = context["layout"]
    resources = context["resources"]
    job = agent["job"]
    basin = sim_resources.point_by_id(layout, job.get("basinId"))
    jar_location = sim_resources.point_by_id(layout, job.get("jarLocationId"))
    if basin is None:
        agent["job"] = None
        return False

    phase = job.get("phase")
    if phase == "to_jar":
        if jar_location is not None and not at_point(agent, jar_location):
            agent["intent"] = {"action": "go_to", "target": jar_location["label"], "reason": "pick up jar"}
            return move_towards(agent, jar_location["position"], dt, context)
        agent["inventory"]["jar"] = True
        agent["inventory"]["jarFilled"] = False
        job["phase"] = "to_water"
        return True

    if phase == "to_water":
        water_position = job.get("waterPosition") or sim_resources.nearest_water_source_position(layout, basin["position"])
        if water_position is None:
            finish_job(agent, "no water source available")
            return False
        if not at_position(agent, water_position, 120.0):
            agent["intent"] = {"action": "go_to", "target": "Water source", "reason": "fill jar"}
            return move_towards(agent, water_position, dt, context)
        agent["inventory"]["jar"] = True
        agent["inventory"]["jarFilled"] = True
        job["phase"] = "to_basin"
        return True

    if phase == "to_basin":
        if not at_point(agent, basin):
            agent["intent"] = {"action": "go_to", "target": basin["label"], "reason": "fill basin"}
            return move_towards(agent, basin["position"], dt, context)
        sim_resources.fill_basin(resources, basin["id"])
        agent["inventory"]["jarFilled"] = False
        job["trips"] = int(job.get("trips", 0)) + 1
        if sim_resources.is_basin_refilled(resources, basin["id"]) or job["trips"] >= sim_resources.WATER_TRIP_LIMIT:
            job["phase"] = "return_jar" if jar_location is not None else "done"
        else:
            job["phase"] = "to_water"
        return True

    if phase == "return_jar":
        if jar_location is not None and not at_point(agent, jar_location):
            agent["intent"] = {"action": "go_to", "target": jar_location["label"], "reason": "drop off jar"}
            return move_towards(agent, jar_location["position"], dt, context)
        agent["inventory"]["jar"] = False
        agent["inventory"]["jarFilled"] = False
        finish_job(agent, "water job complete")
        return True

    agent["inventory"]["jar"] = False
    agent["inventory"]["jarFilled"] = False
    finish_job(agent, "water job complete")
    return True


def advance_hunt_job(agent: dict, dt: float, context: dict) -> bool:
    layout = context["layout"]
    resources = context["resources"]
    rng = context["rng"]
    job = agent["job"]
    fire = sim_resources.point_by_id(layout, job.get("fireId"))
    if fire is None:
        agent["job"] = None
        return False

    if job.get("phase") == "to_pig":
        pig = next((item for item in resources.get("pigs", []) if item["id"] == job.get("pigId")), None)
        if pig is None:
            pig = sim_resources.nearest_north_forest_pig(layout, resources, agent["position"])
            if pig is None:
                finish_job(agent, "no pig available")
                return False
            job["pigId"] = pig["id"]
        if not at_position(agent, pig["position"], agent["radius"] + pig["radius"] + ARRIVAL_EXTRA_MARGIN):
            agent["intent"] = {"action": "go_to", "target": pig["label"], "reason": "hunt pig for fire"}
            return move_towards(agent, pig["position"], dt, context)
        killed = sim_resources.kill_and_respawn_pig(layout, resources, pig["id"], rng)
        if killed is not None:
            agent["inventory"]["rawPig"] = True
        job["phase"] = "to_fire"
        return True

    if job.get("phase") == "to_fire":
        if not at_point(agent, fire):
            agent["intent"] = {"action": "go_to", "target": fire["label"], "reason": "bring raw pig to fire"}
            return move_towards(agent, fire["position"], dt, context)
        if agent["inventory"].get("rawPig") and sim_resources.place_raw_pig(resources, fire["id"]):
            agent["inventory"]["rawPig"] = False
            finish_job(agent, "placed raw pig on fire")
        else:
            agent["inventory"]["rawPig"] = False
            finish_job(agent, "no empty fire slot")
        return True

    finish_job(agent, "hunt job complete")
    return True


def finish_job(agent: dict, reason: str) -> None:
    agent["job"] = None
    agent["intent"] = {"action": "wander", "reason": reason}


def at_point(agent: dict, point: dict) -> bool:
    return at_position(agent, point["position"], agent["radius"] + point["radius"] + ARRIVAL_EXTRA_MARGIN)


def at_position(agent: dict, position: dict, radius: float) -> bool:
    return distance(agent["position"], position) <= radius


def move_towards(agent: dict, target: dict, dt: float, context: dict) -> bool:
    dx = target["x"] - agent["position"]["x"]
    dy = target["y"] - agent["position"]["y"]
    if abs(dx) + abs(dy) <= 0.001:
        return False
    heading = math.atan2(dy, dx)
    agent["targetHeadingRadians"] = heading
    agent["headingRadians"] = step_angle_towards(agent["headingRadians"], heading, agent["turnRate"] * dt * 1.8)
    proposed = {
        "x": agent["position"]["x"] + math.cos(agent["headingRadians"]) * agent["moveSpeed"] * dt,
        "y": agent["position"]["y"] + math.sin(agent["headingRadians"]) * agent["moveSpeed"] * dt,
    }
    clamped, hit_x, hit_y = context["clamp_agent_position"](agent, proposed)
    agent["position"] = clamped
    if hit_x or hit_y:
        agent["targetHeadingRadians"] = context["rng"].uniform(0.0, math.tau)
    return True


def wander(agent: dict, dt: float, context: dict) -> bool:
    rng = context["rng"]
    agent["decisionTimer"] -= dt
    if agent["decisionTimer"] <= 0.0:
        agent["targetHeadingRadians"] = agent["headingRadians"] + rng.uniform(-1.7, 1.7)
        agent["decisionTimer"] = rng.uniform(0.35, 1.4)
    agent["intent"] = {"action": "wander", "reason": "no active resource job"}
    agent["headingRadians"] = step_angle_towards(agent["headingRadians"], agent["targetHeadingRadians"], agent["turnRate"] * dt)
    proposed = {
        "x": agent["position"]["x"] + math.cos(agent["headingRadians"]) * agent["moveSpeed"] * dt,
        "y": agent["position"]["y"] + math.sin(agent["headingRadians"]) * agent["moveSpeed"] * dt,
    }
    clamped, hit_x, hit_y = context["clamp_agent_position"](agent, proposed)
    agent["position"] = clamped
    if hit_x or hit_y:
        agent["targetHeadingRadians"] = rng.uniform(0.0, math.tau)
        agent["decisionTimer"] = rng.uniform(0.12, 0.35)
    return True


def step_angle_towards(current: float, target: float, max_delta: float) -> float:
    delta = math.atan2(math.sin(target - current), math.cos(target - current))
    if abs(delta) <= max_delta:
        return target
    return current + math.copysign(max_delta, delta)
