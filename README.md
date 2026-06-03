# Modeler

Engine-independent core for the Roman vs Ottoman 2D agent simulation.

This repo should not contain an Unreal project during the core-building phase. The simulation, layout model, validation, and debug tooling are built outside Unreal first. Unreal integration happens later through a dedicated adapter/hook layer.

## Start

Desktop shortcut: `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`

Open `ModelerLayoutEditor.pyw` for the native local layout editor.

Double-click `StartModeler.bat` to launch the local editor window from Windows.

Open `RunBlock0ASmoke.exe` to launch the current pure C++ smoke test without typing commands.

`BuildAndTestCore.bat` remains the underlying script if we need to inspect or change the build flow.
`tools/desktop/CreateCurrentSimulationShortcut.ps1` recreates the desktop shortcut if needed.

For the ongoing architecture record, read `Docs/SystemJournal.md`.

## Current Stop Point

Block 0A has been corrected to be engine-independent:

- Shared simulation layout enums.
- Plain C++ layout marker structs.
- Plain C++ layout draft container.
- Block 0A validation-summary stub.
- Smoke test for the pure core.
- Native local layout editor with drag and inspector controls.
- Repo-backed JSON save file for the current layout state.

There is intentionally no `.uproject`, Unreal module, Unreal actor class, or generated Unreal build target in this repo now.

Do not continue to Block 0B until the engine-independent direction is approved.

## Test

1. Open `ModelerLayoutEditor.pyw` and confirm the native editor window opens.
2. Drag a zone, point, and wall endpoint to confirm direct manipulation works.
3. Confirm `Ctrl+Z` undoes the last layout edit.
4. Confirm mouse-wheel zoom and right-drag panning work on the map.
5. Change `Label Text Size` and confirm the on-map text updates.
6. Click `Save Layout` or press `Ctrl+S` to explicitly write the current draft to `data/current_layout.json`.
7. Close and reopen the editor without saving a fresh edit, and confirm it returns to the last explicit save rather than unsaved session changes.
8. Open `RunBlock0ASmoke.exe`.
9. Confirm the console reports marker counts.
10. Confirm it prints `Block 0A pure core smoke test passed.`
