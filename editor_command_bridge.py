from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent
COMMAND_PATH = ROOT / "data" / "editor_command.json"
STATUS_PATH = ROOT / "data" / "editor_command_status.json"
COMMAND_POLL_MS = 500
ACTION_REFRESH = "refresh"
ACTION_PING = "ping"
BRIDGE_STATE_ATTR = "_modeler_command_bridge_state"


def latest_command_id() -> str | None:
    command = read_command()
    if command is None:
        return None
    return str(command.get("id", "")) or None


def read_command() -> dict | None:
    try:
        payload = json.loads(COMMAND_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if not payload.get("id") or not payload.get("action"):
        return None
    return payload


def read_pending_command(last_handled_id: str | None) -> dict | None:
    command = read_command()
    if command is None:
        return None
    command_id = str(command["id"])
    if command_id == last_handled_id:
        return None
    return command


def write_command(action: str, payload: dict | None = None) -> dict:
    command = {
        "id": f"{time.time_ns()}-{os.getpid()}",
        "action": action,
        "payload": payload or {},
        "createdAt": time.time(),
        "pid": os.getpid(),
    }
    atomic_write_json(COMMAND_PATH, command)
    return command


def read_status() -> dict | None:
    try:
        payload = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_status(command: dict, state: str, message: str) -> None:
    status = {
        "id": str(command.get("id", "")),
        "action": str(command.get("action", "")),
        "state": state,
        "message": message,
        "handledAt": time.time(),
        "pid": os.getpid(),
    }
    atomic_write_json(STATUS_PATH, status)


def wait_for_status(command_id: str, timeout_seconds: float) -> dict | None:
    deadline = time.time() + max(0.0, timeout_seconds)
    while time.time() <= deadline:
        status = read_status()
        if status is not None and str(status.get("id", "")) == command_id:
            return status
        time.sleep(0.1)
    return None


def command_file_mtime() -> float:
    try:
        return COMMAND_PATH.stat().st_mtime
    except OSError:
        return 0.0


def install_tk_command_bridge(root, handlers: dict[str, Callable[[dict], str | None]]) -> None:
    state = getattr(root, BRIDGE_STATE_ATTR, None)
    if state is None:
        state = {
            "last_id": latest_command_id(),
            "last_mtime": command_file_mtime(),
            "handlers": {},
        }
        setattr(root, BRIDGE_STATE_ATTR, state)
        root.after(COMMAND_POLL_MS, lambda: poll_tk_command_bridge(root))
    state["handlers"].update(handlers)


def poll_tk_command_bridge(root) -> None:
    state = getattr(root, BRIDGE_STATE_ATTR, None)
    if state is None:
        return

    try:
        current_mtime = command_file_mtime()
        if current_mtime != state.get("last_mtime"):
            state["last_mtime"] = current_mtime
            command = read_pending_command(state.get("last_id"))
            if command is not None:
                state["last_id"] = str(command["id"])
                handle_tk_command(state, command)
    except Exception as error:
        write_status({"id": state.get("last_id"), "action": "bridge"}, "error", f"Command bridge failed: {error}")
    finally:
        try:
            root.after(COMMAND_POLL_MS, lambda: poll_tk_command_bridge(root))
        except RuntimeError:
            pass


def handle_tk_command(state: dict, command: dict) -> None:
    action = str(command.get("action", ""))
    handler = state["handlers"].get(action)
    if handler is None:
        write_status(command, "error", f"Unknown editor command: {action}")
        return

    try:
        message = handler(command) or f"Handled editor command: {action}"
        write_status(command, "ok", message)
    except Exception as error:
        write_status(command, "error", f"Editor command failed: {error}")


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)
