from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import editor_command_bridge


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a command to the open Modeler editor.")
    parser.add_argument("action", nargs="?", default=editor_command_bridge.ACTION_PING)
    parser.add_argument("--wait", type=float, default=0.0, help="Seconds to wait for a matching status response.")
    args = parser.parse_args()

    command = editor_command_bridge.write_command(args.action)
    result = {"command": command}
    exit_code = 0

    if args.wait > 0.0:
        status = editor_command_bridge.wait_for_status(command["id"], args.wait)
        result["status"] = status
        if status is None:
            exit_code = 2
        elif status.get("state") != "ok":
            exit_code = 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
