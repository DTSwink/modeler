# Start Here

## Open The Local Entry Point

Desktop shortcut: `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`

Open `ModelerLayoutEditor.pyw` for the native local layout editor.

Double-click `StartModeler.bat` to launch the editor from Windows.

## Run The Current Module

Open `RunBlock0ASmoke.exe` to launch the current engine-independent smoke test without typing commands.

`BuildAndTestCore.bat` remains the underlying script.

## Current Work Gate

The repo is intentionally stopped at Block 0A. The current task is to approve the engine-independent foundation before Block 0B begins.

## Main References

- `README.md`: quick project status and test checklist.
- `Docs/SystemJournal.md`: living journal of how the system works.
- `ModelerLayoutEditor.pyw`: primary native local editor for the latest sim state.
- `include/modeler/sim/`: public pure C++ sim headers.
- `src/modeler/sim/`: pure C++ sim implementation.
- `tests/block0a_smoke.cpp`: current smoke test.
- `BuildAndTestCore.bat`: double-click build/test launcher.
- `RunBlock0ASmoke.exe`: Windows wrapper that launches the smoke test script.
- `tools/desktop/CreateCurrentSimulationShortcut.ps1`: recreates the desktop shortcut if needed.

## Important Boundary

There is no Unreal project here right now. Unreal is only a future integration target.

The browser viewer has been retired. The intended user-facing surface is the native local editor window instead.
