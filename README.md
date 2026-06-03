# Modeler

Engine-independent core for the Roman vs Ottoman 2D agent simulation.

The native layout editor in this repo is not just a preview. It is the live authoring surface for the future simulation, and the saved layout data here should be treated as the next blocks' input map.

The same native editor is now also the first runtime sandbox. Roman-side prototype agents spawn from the authored Roman camp, then roam across the full authored map, so layout work and early simulation debugging happen in one place instead of splitting across tools.

The runtime stepping logic and saved camera-state logic are now split into dedicated helper modules so those behaviors can evolve without forcing unrelated editor UI changes.

The future game core is intended to stay headless. Rendering and editor presentation are host layers around the simulation, not part of the simulation itself.

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
- Hover-driven labels on the main zone/location body plus clearer location markers so the map stays readable as agent detail grows.
- First Roman-only runtime simulation pass with five draggable agents, play/pause, and time-speed control inside the native editor.
- Optional `Freeze Layout` toggle so the map can stay readable during simulation without accidental handle grabs or layout drags.
- Spacebar toggles the simulation without re-triggering the last clicked button.
- `Save Layout` also persists the current zoom/pan view so refreshes reopen from the same camera framing.

There is intentionally no `.uproject`, Unreal module, Unreal actor class, or generated Unreal build target in this repo now.

Do not continue to Block 0B until the engine-independent direction is approved.

## Test

1. Open `ModelerLayoutEditor.pyw` and confirm the native editor window opens.
2. Drag a zone, location, and wall endpoint to confirm direct manipulation works.
3. Confirm watchtower and other location clicks feel tight to the visible marker rather than a large hidden radius.
4. Confirm dragging one zone corner only moves the adjacent edges while the opposite corner stays fixed.
5. Confirm the map stays visually quiet until you hover a zone or location, and that hovered labels appear above geometry.
6. Confirm `Label Mode` is set to `Hover` for the current saved layouts.
7. Confirm `Ctrl+Z` undoes the last layout edit.
8. Confirm mouse-wheel zoom and right-drag panning work on the map.
9. Change `Label Text Size` and confirm the on-map text updates.
10. Confirm the tent, infirmary, and training areas exist inside each camp, and the old grass hallway is gone.
11. Click `Play` and confirm five Roman agents begin wandering across the map.
12. Change the simulation speed and confirm time dilation/compression visibly changes agent motion.
13. Drag an agent and confirm its coordinates stay capped by the map extents rather than the Roman camp footprint.
14. Toggle `Freeze Layout` on and confirm hovering still works while layout handles and map drag edits stop responding.
15. Toggle `Freeze Layout` off and confirm zones, locations, and walls are editable again even if the simulation is still running.
16. Press the spacebar and confirm it toggles play/pause instead of retriggering the last button action.
17. Save the layout, refresh or reopen the editor, and confirm the camera zoom/pan reopens where it was saved.
18. Click `Save Layout` or press `Ctrl+S` to explicitly write the current draft to `data/current_layout.json`.
19. Close and reopen the editor without saving a fresh edit, and confirm it returns to the last explicit save rather than unsaved session changes.
20. Open `RunBlock0ASmoke.exe`.
21. Confirm the console reports marker counts.
22. Confirm it prints `Block 0A pure core smoke test passed.`
