# Start Here

## Open The Local Entry Point

Desktop shortcut: `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`

Open `CurrentSimulation.html` for the rendered current-state sim page.

Double-click `StartModeler.bat` or `OpenCurrentSimulation.bat` to open that page from Windows.

## Run The Current Module

Open `RunBlock0ASmoke.exe` to launch the current engine-independent smoke test without typing commands.

`BuildAndTestCore.bat` remains the underlying script.

## Current Work Gate

The repo is intentionally stopped at Block 0A. The current task is to approve the engine-independent foundation before Block 0B begins.

## Main References

- `README.md`: quick project status and test checklist.
- `Docs/SystemJournal.md`: living journal of how the system works.
- `CurrentSimulation.html`: primary visual snapshot for the latest local sim state.
- `include/modeler/sim/`: public pure C++ sim headers.
- `src/modeler/sim/`: pure C++ sim implementation.
- `tests/block0a_smoke.cpp`: current smoke test.
- `BuildAndTestCore.bat`: double-click build/test launcher.
- `RunBlock0ASmoke.exe`: Windows wrapper that launches the smoke test script.
- `tools/desktop/CreateCurrentSimulationShortcut.ps1`: recreates the desktop shortcut if needed.

## Important Boundary

There is no Unreal project here right now. Unreal is only a future integration target.

Codex desktop file links preview text files in the editor, which is why `.bat` links show source instead of running. Prefer the HTML launch page and the `.exe` launcher for clickable entry points.
