from __future__ import annotations


LIMB_TYPES = (
    "head",
    "torso",
    "left_arm",
    "right_arm",
    "left_leg",
    "right_leg",
)
DEFAULT_ATTACK_LIMB = "torso"
LIMB_LABELS = {
    "head": "Head",
    "torso": "Torso",
    "left_arm": "Left Arm",
    "right_arm": "Right Arm",
    "left_leg": "Left Leg",
    "right_leg": "Right Leg",
}


def build_default_body_state() -> dict:
    return {
        "limbs": {limb: build_limb_state(limb) for limb in LIMB_TYPES},
        "lastWound": None,
    }


def build_limb_state(limb: str) -> dict:
    limb_id = normalize_limb(limb)
    return {
        "id": limb_id,
        "label": LIMB_LABELS[limb_id],
        "wounds": [],
    }


def normalize_body_state(living: dict) -> None:
    body = living.get("body") if isinstance(living.get("body"), dict) else {}
    limbs = body.get("limbs") if isinstance(body.get("limbs"), dict) else {}
    normalized_limbs = {}
    for limb in LIMB_TYPES:
        limb_state = limbs.get(limb) if isinstance(limbs.get(limb), dict) else {}
        limb_state["id"] = limb
        limb_state["label"] = LIMB_LABELS[limb]
        wounds = limb_state.get("wounds") if isinstance(limb_state.get("wounds"), list) else []
        limb_state["wounds"] = [normalize_wound(wound, fallback_limb=limb) for wound in wounds if isinstance(wound, dict)]
        normalized_limbs[limb] = limb_state
    body["limbs"] = normalized_limbs
    last_wound = body.get("lastWound")
    body["lastWound"] = normalize_wound(last_wound) if isinstance(last_wound, dict) else None
    living["body"] = body


def normalize_limb(value, *, default: str = DEFAULT_ATTACK_LIMB) -> str:
    text = str(value or default).strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in LIMB_TYPES else default


def limb_label(limb: str) -> str:
    return LIMB_LABELS[normalize_limb(limb)]


def normalize_wound(wound: dict, *, fallback_limb: str = DEFAULT_ATTACK_LIMB) -> dict:
    limb = normalize_limb(wound.get("limb"), default=fallback_limb)
    return {
        "limb": limb,
        "label": limb_label(limb),
        "severity": str(wound.get("severity", "wounded")),
        "source": str(wound.get("source", "unknown")),
    }


def record_wound(living: dict, *, limb: str = DEFAULT_ATTACK_LIMB, severity: str = "wounded", source: str = "unknown") -> dict:
    normalize_body_state(living)
    wound = normalize_wound({"limb": limb, "severity": severity, "source": source})
    living["body"]["limbs"][wound["limb"]]["wounds"].append(wound)
    living["body"]["lastWound"] = wound
    health = living.get("health") if isinstance(living.get("health"), dict) else {}
    wounds = health.get("wounds") if isinstance(health.get("wounds"), list) else []
    wounds.append(wound)
    health["wounds"] = wounds
    current_status = str(health.get("status", "alive")).strip().lower()
    if wound["severity"] == "fatal":
        health["status"] = "dead"
    elif current_status == "alive":
        health["status"] = "wounded walking"
    living["health"] = health
    return wound
