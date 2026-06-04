from __future__ import annotations

import math
import random

import living_body
import perception
import sim_resources
from sim_geometry import clamp, distance


HUNGER_DEPLETION_PER_SECOND = 0.34
THIRST_DEPLETION_PER_SECOND = 0.52
NEED_CHECK_INTERVAL_MIN = 0.45
NEED_CHECK_INTERVAL_MAX = 1.15
RESOURCE_INTERACTION_EXTRA = 18.0
RESOURCE_INTERACTION_RADIUS_MIN = 72.0
RESOURCE_POINT_RADIUS_CAP = 90.0
ATTACK_INTERACTION_EXTRA = 14.0
ATTACK_INTERACTION_RADIUS_MIN = 76.0
ATTACK_TARGET_RADIUS_CAP = 80.0
WATER_INTERACTION_RADIUS = 72.0


def normalize_brain_state(agent: dict) -> None:
    agent.setdefault("brain", "NeedsWorker")
    agent.setdefault("intent", {"action": "wander", "reason": "initializing"})
    agent.setdefault("job", None)
    inventory = agent.get("inventory") if isinstance(agent.get("inventory"), dict) else {}
    inventory.setdefault("jar", False)
    inventory.setdefault("jarFilled", False)
    inventory.setdefault("rawPig", False)
    inventory.setdefault("rawPigLabel", None)
    inventory.setdefault("rawPigBody", None)
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
    remembered_empty_slots = sim_resources.fire_empty_slot_count(resources, fire["id"])
    dead_pig = perception.nearest_visible_dead_pig(agent, resources)
    if dead_pig is not None:
        assign_dead_pig_pickup_job(agent, dead_pig, fire, "dead pig seen in cone", remembered_empty_slots=remembered_empty_slots)
        return
    target = sim_resources.nearest_attack_target(
        layout,
        resources,
        agent["position"],
        {"kind": "pig", "forest": "north"},
    )
    if target is None:
        agent["intent"] = {"action": "wander", "reason": "no north forest pig available"}
        return
    agent["job"] = {
        "type": "hunt_food",
        "phase": "attack_target",
        "fireId": fire["id"],
        "rememberedEmptySlots": remembered_empty_slots,
        "seenDeadPigCarriers": [],
        "attack": {
            "target": sim_resources.attack_target_ref(target),
            "targetLimb": living_body.DEFAULT_ATTACK_LIMB,
            "reacquire": {"kind": "pig", "forest": "north"},
            "reason": "hunt pig for fire",
            "onDefeat": "carry_raw_pig",
        },
    }
    agent["intent"] = {"action": "go_to", "target": target["label"], "reason": "fire has an empty slot"}


def assign_dead_pig_pickup_job(
    agent: dict,
    dead_pig: dict,
    fire: dict,
    reason: str,
    *,
    remembered_empty_slots: int,
) -> None:
    agent["job"] = {
        "type": "hunt_food",
        "phase": "pickup_dead_pig",
        "fireId": fire["id"],
        "deadPigId": dead_pig["id"],
        "rememberedEmptySlots": remembered_empty_slots,
        "seenDeadPigCarriers": [],
        "attack": {
            "target": {
                "kind": "dead_pig",
                "id": dead_pig["id"],
                "label": dead_pig["label"],
                "radius": dead_pig.get("radius", 70.0),
                "targetLimb": living_body.DEFAULT_ATTACK_LIMB,
            },
            "targetLimb": living_body.DEFAULT_ATTACK_LIMB,
            "reacquire": {"kind": "pig", "forest": "north"},
            "reason": "pick up dead pig",
            "onDefeat": "carry_raw_pig",
        },
    }
    agent["intent"] = {"action": "go_to", "target": dead_pig["label"], "reason": reason}


def advance_job(agent: dict, dt: float, context: dict) -> bool:
    job_type = agent["job"].get("type")
    if job_type == "drink":
        return advance_drink_job(agent, dt, context)
    if job_type == "eat":
        return advance_eat_job(agent, dt, context)
    if job_type == "fetch_water":
        return advance_water_job(agent, dt, context)
    if job_type in {"hunt_food", "hunt_pig"}:
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
        emit_interaction(context, agent, "drink", basin, "Basin")
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
        emit_interaction(context, agent, "eat", fire, "Fire")
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
        emit_interaction(context, agent, "pick_up_jar", jar_location or basin, "Jar")
        job["phase"] = "to_water"
        return True

    if phase == "to_water":
        water_position = job.get("waterPosition") or sim_resources.nearest_water_source_position(layout, basin["position"])
        if water_position is None:
            finish_job(agent, "no water source available")
            return False
        if not at_position(agent, water_position, WATER_INTERACTION_RADIUS):
            agent["intent"] = {"action": "go_to", "target": "Water source", "reason": "fill jar"}
            return move_towards(agent, water_position, dt, context)
        agent["inventory"]["jar"] = True
        agent["inventory"]["jarFilled"] = True
        emit_interaction(context, agent, "fill_jar", {"label": "Water source", "position": water_position}, "Water")
        job["phase"] = "to_basin"
        return True

    if phase == "to_basin":
        if not at_point(agent, basin):
            agent["intent"] = {"action": "go_to", "target": basin["label"], "reason": "fill basin"}
            return move_towards(agent, basin["position"], dt, context)
        filled = sim_resources.fill_basin(resources, basin["id"])
        if filled > 0.0:
            emit_interaction(context, agent, "fill_basin", basin, "Basin")
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
        emit_interaction(context, agent, "drop_jar", jar_location or basin, "Jar")
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
    normalize_attack_job(job)
    fire = sim_resources.point_by_id(layout, job.get("fireId"))
    if fire is None:
        agent["job"] = None
        return False
    job.setdefault("rememberedEmptySlots", max(1, sim_resources.fire_empty_slot_count(resources, fire["id"])))
    job.setdefault("seenDeadPigCarriers", [])

    if job.get("phase") in {"attack_target", "pickup_dead_pig"} and should_return_because_seen_carriers(agent, context, job):
        job["phase"] = "return_to_fire"
        agent["intent"] = {"action": "go_to", "target": fire["label"], "reason": "enough pig carriers seen"}
        return True

    if job.get("phase") == "attack_target":
        visible_dead_pig = perception.nearest_visible_dead_pig(agent, resources)
        if visible_dead_pig is not None:
            job["phase"] = "pickup_dead_pig"
            job["deadPigId"] = visible_dead_pig["id"]
            agent["intent"] = {"action": "go_to", "target": visible_dead_pig["label"], "reason": "dead pig seen in cone"}
            return True
        attack = job.get("attack", {})
        target_ref = attack.get("target")
        target_limb = living_body.normalize_limb(attack.get("targetLimb"))
        attack["targetLimb"] = target_limb
        target = sim_resources.attack_target_by_ref(layout, resources, target_ref)
        if target is None:
            target = sim_resources.nearest_attack_target(layout, resources, agent["position"], attack.get("reacquire", {}))
            if target is None:
                finish_job(agent, "no attack target available")
                return False
            target_ref = sim_resources.attack_target_ref(target)
            target_ref["targetLimb"] = target_limb
            attack["target"] = target_ref
        elif isinstance(target_ref, dict):
            target_ref["targetLimb"] = target_limb
        attack_radius = attack_interaction_radius(agent, target)
        if not at_position(agent, target["position"], attack_radius):
            agent["intent"] = {"action": "attack_target", "target": target["label"], "reason": attack.get("reason", "attack target")}
            return move_towards(agent, target["position"], dt, context)
        defeated = sim_resources.defeat_attack_target(layout, resources, target_ref, rng)
        if defeated is not None and attack.get("onDefeat") == "carry_raw_pig":
            carry_dead_pig(agent, defeated)
            emit_interaction(context, agent, "attack_target", defeated, defeated.get("kind", "target"), target_limb=target_limb)
        job["phase"] = "to_fire"
        return True

    if job.get("phase") == "pickup_dead_pig":
        dead_pig = sim_resources.dead_pig_by_id(resources, job.get("deadPigId"))
        if dead_pig is None:
            job["phase"] = "attack_target"
            return True
        if not at_position(agent, dead_pig["position"], attack_interaction_radius(agent, dead_pig)):
            agent["intent"] = {"action": "go_to", "target": dead_pig["label"], "reason": "pick up dead pig"}
            return move_towards(agent, dead_pig["position"], dt, context)
        picked_up = sim_resources.pick_up_dead_pig(resources, dead_pig["id"])
        if picked_up is None:
            job["phase"] = "attack_target"
            return True
        carry_dead_pig(agent, picked_up)
        emit_interaction(context, agent, "pick_up_dead_pig", picked_up, "Dead Pig")
        job["phase"] = "to_fire"
        return True

    if job.get("phase") == "return_to_fire":
        if not at_point(agent, fire):
            agent["intent"] = {"action": "go_to", "target": fire["label"], "reason": "enough pig carriers seen"}
            return move_towards(agent, fire["position"], dt, context)
        finish_job(agent, "returned because enough pig carriers were seen")
        return True

    if job.get("phase") == "to_fire":
        if not at_point(agent, fire):
            agent["intent"] = {"action": "go_to", "target": fire["label"], "reason": "bring raw pig to fire"}
            return move_towards(agent, fire["position"], dt, context)
        if agent["inventory"].get("rawPig") and sim_resources.place_raw_pig(resources, fire["id"]):
            clear_carried_raw_pig(agent)
            emit_interaction(context, agent, "place_raw_pig", fire, "Fire")
            finish_job(agent, "placed raw pig on fire")
        else:
            if agent["inventory"].get("rawPig"):
                dropped = sim_resources.drop_dead_pig(
                    resources,
                    agent["position"],
                    label=agent["inventory"].get("rawPigLabel"),
                    body=agent["inventory"].get("rawPigBody"),
                )
                emit_interaction(context, agent, "drop_dead_pig", dropped, "Dead Pig")
            clear_carried_raw_pig(agent)
            finish_job(agent, "no empty fire slot; dropped dead pig")
        return True

    finish_job(agent, "hunt job complete")
    return True


def should_return_because_seen_carriers(agent: dict, context: dict, job: dict) -> bool:
    if agent.get("inventory", {}).get("rawPig"):
        return False
    remembered_empty_slots = int(job.get("rememberedEmptySlots", 0))
    if remembered_empty_slots <= 0:
        return True
    seen_carriers = job.setdefault("seenDeadPigCarriers", [])
    seen_ids = set(seen_carriers)
    for carrier in perception.visible_dead_pig_carriers(agent, context.get("agents", [])):
        carrier_id = carrier.get("id")
        if not carrier_id or carrier_id in seen_ids:
            continue
        seen_ids.add(carrier_id)
        seen_carriers.append(carrier_id)
    return len(seen_ids) >= remembered_empty_slots


def normalize_attack_job(job: dict) -> None:
    if job.get("type") != "hunt_pig":
        return
    job["type"] = "hunt_food"
    job["phase"] = "attack_target"
    job.setdefault("rememberedEmptySlots", 1)
    job.setdefault("seenDeadPigCarriers", [])
    job["attack"] = {
        "target": {
            "kind": "pig",
            "id": job.get("pigId"),
            "label": job.get("pigId") or "Pig",
            "radius": 75.0,
            "targetLimb": living_body.DEFAULT_ATTACK_LIMB,
        },
        "targetLimb": living_body.DEFAULT_ATTACK_LIMB,
        "reacquire": {"kind": "pig", "forest": "north"},
        "reason": "hunt pig for fire",
        "onDefeat": "carry_raw_pig",
    }


def emit_interaction(
    context: dict,
    agent: dict,
    kind: str,
    target: dict,
    target_kind: str,
    *,
    target_limb: str | None = None,
) -> None:
    callback = context.get("emit_interaction")
    if callback is None:
        return
    position = target.get("position", agent["position"])
    callback(
        agent,
        kind,
        target_label=target.get("label", target_kind),
        position=position,
        target_kind=target_kind,
        target_limb=target_limb,
    )


def finish_job(agent: dict, reason: str) -> None:
    agent["job"] = None
    agent["intent"] = {"action": "wander", "reason": reason}


def at_point(agent: dict, point: dict) -> bool:
    return at_position(agent, point["position"], point_interaction_radius(agent, point))


def at_position(agent: dict, position: dict, radius: float) -> bool:
    return distance(agent["position"], position) <= radius


def point_interaction_radius(agent: dict, point: dict) -> float:
    return max(
        RESOURCE_INTERACTION_RADIUS_MIN,
        float(agent.get("radius", 90.0)) * 0.35
        + min(float(point.get("radius", 90.0)), RESOURCE_POINT_RADIUS_CAP) * 0.35
        + RESOURCE_INTERACTION_EXTRA,
    )


def attack_interaction_radius(agent: dict, target: dict) -> float:
    return max(
        ATTACK_INTERACTION_RADIUS_MIN,
        float(agent.get("radius", 90.0)) * 0.45
        + min(float(target.get("radius", 75.0)), ATTACK_TARGET_RADIUS_CAP) * 0.45
        + ATTACK_INTERACTION_EXTRA,
    )


def carry_dead_pig(agent: dict, dead_pig: dict) -> None:
    inventory = agent["inventory"]
    inventory["rawPig"] = True
    inventory["rawPigLabel"] = dead_pig.get("label", "Dead Pig")
    inventory["rawPigBody"] = dead_pig.get("body")


def clear_carried_raw_pig(agent: dict) -> None:
    inventory = agent["inventory"]
    inventory["rawPig"] = False
    inventory["rawPigLabel"] = None
    inventory["rawPigBody"] = None


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
