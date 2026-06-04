from __future__ import annotations

import math

from sim_geometry import clamp


AGENT_STATUS_VALUES = (
    "alive",
    "wounded walking",
    "wounded",
    "dead",
)


def build_default_agent_state() -> dict:
    return {
        "needs": {
            "hunger": 100,
            "thirst": 100,
        },
        "health": {
            "status": AGENT_STATUS_VALUES[0],
        },
        "brain": "NeedsWorker",
        "intent": {
            "action": "wander",
            "reason": "initializing",
        },
        "job": None,
        "inventory": {
            "jar": False,
            "jarFilled": False,
            "rawPig": False,
        },
        "needCheckTimer": 0.0,
    }


def normalize_agent_state(agent: dict) -> None:
    needs = agent.get("needs") if isinstance(agent.get("needs"), dict) else {}
    health = agent.get("health") if isinstance(agent.get("health"), dict) else {}
    inventory = agent.get("inventory") if isinstance(agent.get("inventory"), dict) else {}

    needs["hunger"] = _bounded_int(needs.get("hunger"), default=100)
    needs["thirst"] = _bounded_int(needs.get("thirst"), default=100)

    status = str(health.get("status", AGENT_STATUS_VALUES[0])).strip().lower()
    if status not in AGENT_STATUS_VALUES:
        status = AGENT_STATUS_VALUES[0]
    health["status"] = status

    agent["needs"] = needs
    agent["health"] = health
    agent.setdefault("brain", "NeedsWorker")
    agent.setdefault("intent", {"action": "wander", "reason": "initializing"})
    agent.setdefault("job", None)
    inventory.setdefault("jar", False)
    inventory.setdefault("jarFilled", False)
    inventory.setdefault("rawPig", False)
    agent["inventory"] = inventory
    agent.setdefault("needCheckTimer", 0.0)


def agent_snapshot_sections(agent: dict) -> list[dict]:
    normalize_agent_state(agent)
    return [
        {
            "title": "Health",
            "rows": [
                {"label": "Status", "value": agent["health"]["status"].title()},
            ],
        },
        {
            "title": "Needs",
            "rows": [
                {"label": "Hunger", "value": agent["needs"]["hunger"], "kind": "meter", "maximum": 100},
                {"label": "Thirst", "value": agent["needs"]["thirst"], "kind": "meter", "maximum": 100},
            ],
        },
        {
            "title": "Decision",
            "rows": [
                {"label": "Brain", "value": agent["brain"]},
                {"label": "Intent", "value": _format_intent(agent.get("intent"))},
                {"label": "Job", "value": _format_job(agent.get("job"))},
                {"label": "Carrying", "value": _format_inventory(agent.get("inventory"))},
            ],
        },
        {
            "title": "Movement",
            "rows": [
                {"label": "Position X", "value": _format_float(agent["position"]["x"])},
                {"label": "Position Y", "value": _format_float(agent["position"]["y"])},
                {"label": "Move Speed", "value": _format_float(agent["moveSpeed"])},
                {"label": "Radius", "value": _format_float(agent["radius"])},
                {"label": "Heading", "value": _format_angle(agent["headingRadians"])},
                {"label": "Target Heading", "value": _format_angle(agent["targetHeadingRadians"])},
                {"label": "Turn Rate", "value": _format_float(agent["turnRate"], digits=2)},
                {"label": "Decision Timer", "value": f"{max(0.0, float(agent['decisionTimer'])):.2f}s"},
            ],
        },
        {
            "title": "Identity",
            "rows": [
                {"label": "Id", "value": agent["id"]},
                {"label": "Label", "value": agent["label"]},
                {"label": "Faction", "value": agent["faction"]},
            ],
        },
    ]


def _bounded_int(value, *, default: int) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return clamp(numeric, 0.0, 100.0)


def _format_angle(angle_radians: float) -> str:
    return f"{math.degrees(float(angle_radians)):.1f} deg"


def _format_float(value: float, *, digits: int = 1) -> str:
    return f"{float(value):.{digits}f}"


def _format_intent(intent) -> str:
    if not isinstance(intent, dict):
        return "None"
    action = str(intent.get("action", "none"))
    target = intent.get("target")
    reason = intent.get("reason")
    parts = [action]
    if target:
        parts.append(f"to {target}")
    if reason:
        parts.append(f"({reason})")
    return " ".join(parts)


def _format_job(job) -> str:
    if not isinstance(job, dict):
        return "None"
    job_type = str(job.get("type", "unknown"))
    phase = job.get("phase")
    if phase:
        return f"{job_type} / {phase}"
    return job_type


def _format_inventory(inventory) -> str:
    if not isinstance(inventory, dict):
        return "Empty"
    carried = []
    if inventory.get("jarFilled"):
        carried.append("full jar")
    elif inventory.get("jar"):
        carried.append("jar")
    if inventory.get("rawPig"):
        carried.append("raw pig")
    return ", ".join(carried) if carried else "Empty"
