# Modeler

Engine-independent core for the Roman vs Ottoman 2D agent simulation.

The native layout editor in this repo is not just a preview. It is the live authoring surface for the future simulation, and the saved layout data here should be treated as the next blocks' input map.

For UI cleanup and readability review, prefer user-provided screenshots plus background or headless checks before foreground launches when possible. That lets us tune the editor without taking over the active screen.

This repo should not contain an Unreal project during the core-building phase. The simulation, layout model, validation, and debug tooling are built outside Unreal first. Unreal integration happens later through a dedicated adapter/hook layer.

## Start

Desktop shortcut: `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`

Open `ModelerLayoutEditor.pyw` for the native local layout editor.

Double-click `StartModeler.bat` to launch the local editor window from Windows.

The launcher is meant to open the latest editor build. If editor code changed on disk after a window was already running, a fresh instance should open instead of reviving the stale one. The editor title and top metadata also carry a UI build stamp so outdated windows are easier to spot.

Inside the editor, use `Refresh App` or `Ctrl+R` to relaunch into the newest local build without manually closing the window first. If there are unsaved layout edits, the refresh action prompts before continuing.

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
- Camp sub-areas for tents, infirmaries, and training grounds.
- Adaptive label density and decluttered on-map callouts for readability at whole-scene scale.

There is intentionally no `.uproject`, Unreal module, Unreal actor class, or generated Unreal build target in this repo now.

Do not continue to Block 0B until the engine-independent direction is approved.

## Test

1. Open `ModelerLayoutEditor.pyw` and confirm the native editor window opens.
2. Drag a zone, point, and wall endpoint to confirm direct manipulation works.
3. Confirm watchtower and other point clicks feel tight to the visible marker rather than a large hidden radius.
4. Confirm dragging one zone corner only moves the adjacent edges while the opposite corner stays fixed.
5. Confirm the full-scene view is readable: major region labels stay visible, dense camp detail labels stay quieter until you zoom in or select them.
6. Confirm `Label Density` changes what is shown on the map.
7. Confirm `Ctrl+Z` undoes the last layout edit.
8. Confirm mouse-wheel zoom and right-drag panning work on the map.
9. Change `Label Text Size` and confirm the on-map text updates.
10. Confirm the tent, infirmary, and training areas exist inside each camp, and the old grass hallway is gone.
11. Click `Save Layout` or press `Ctrl+S` to explicitly write the current draft to `data/current_layout.json`.
12. Close and reopen the editor without saving a fresh edit, and confirm it returns to the last explicit save rather than unsaved session changes.
13. Open `RunBlock0ASmoke.exe`.
14. Confirm the console reports marker counts.
15. Confirm it prints `Block 0A pure core smoke test passed.`
