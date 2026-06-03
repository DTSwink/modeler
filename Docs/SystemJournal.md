# System Journal

This is the living technical journal for the Roman vs Ottoman 2D agent simulation. Keep it detailed enough that a new implementation pass can resume safely, but concise enough to scan before working.

## Update Rule

Update this journal after every implementation block or meaningful architecture change. Record:

- Current stop point.
- What exists now.
- How the pieces fit together.
- How to test the current block.
- What must wait until later blocks.

## Current Stop Point

The project now has its first live agent-simulation pass inside the native editor.

The project is now engine-independent. The core sim, layout model, validation, debug tools, and future behavior systems should be built outside Unreal first. Unreal should only receive a later adapter/hook layer after the core behavior is useful and stable.

There is intentionally no `.uproject`, Unreal module, Unreal actor class, Unreal build target, or Unreal-generated runtime code in the tracked project.

## Non-Negotiable Direction

Build the system off Unreal first.

Unreal is a final host/integration target, not the foundation. The sim should not depend on Unreal types such as `AActor`, `UObject`, `FVector`, `FName`, `TArray`, reflection macros, Actor ticking, or editor-only buttons. When Unreal integration eventually starts, the adapter should translate between Unreal objects and the pure core data model.

Expected future shape:

- `include/` and `src/`: pure core simulation and layout logic.
- `tests/`: pure core tests and smoke tests.
- `tools/`: standalone editors, visualizers, or debugging tools if needed.
- `adapters/unreal/`: future bridge layer, added only when the core is ready to hook into Unreal.

## Core Principle

The player is never a special simulation entity. Later, player control should be represented by assigning an ordinary agent a `PlayerInput` brain. The agent keeps its normal faction, role, position, state, and capabilities.

The layout editor is also part of that core direction. Treat the saved layout JSON as authored simulation input, not disposable mockup data. Future validation, baking, placement logic, and early runtime systems should read from this authored layout instead of inventing a separate temporary map source.

UI readability matters now, not later. The editor is heading toward agent overlays, so the whole-scene view needs strong visual hierarchy before we add more moving parts.

The simulation surface should stay unified with the authoring surface. Early runtime behavior is supposed to read from the same authored layout the user is editing, not from a detached mock scene.

## Project Shape

Important files:

- `ModelerLayoutEditor.pyw`: primary native local editor for the latest sim state.
- `ModelerLayoutEditorLauncher.exe`: native Windows launcher used by the desktop shortcut.
- `include/modeler/sim/SimTypes.h`: shared layout enums.
- `include/modeler/sim/LayoutMarkers.h`: engine-independent marker data.
- `src/modeler/sim/LayoutMarkers.cpp`: Block 0A marker summary/validation stub.
- `tests/block0a_smoke.cpp`: current smoke test.
- `data/default_layout.json`: reset source for the editor.
- `data/current_layout.json`: last explicit saved layout for the editor.
- `tools/launchers/ModelerLayoutEditorLauncher.cpp`: Windows launcher source for the native editor.
- `tools/launchers/RunBlock0ASmoke.cpp`: Windows launcher source for the smoke test wrapper.
- `tools/desktop/CreateCurrentSimulationShortcut.ps1`: recreates the desktop shortcut if needed.
- `RunBlock0ASmoke.exe`: Windows wrapper that launches the smoke test script.
- `BuildAndTestCore.bat`: double-click build/test launcher.
- `StartModeler.bat`: opens the native local editor launcher.

Local convenience artifact:

- `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`: desktop shortcut that opens the native editor.

Generated folders such as `Build`, `Out`, `Binaries`, `Intermediate`, `Saved`, and `DerivedDataCache` are ignored by git.

## Block 0A Components

`Faction` identifies semantic ownership:

- `Neutral`
- `Roman`
- `Ottoman`
- `Wildlife`

`ZoneType` identifies rectangular area semantics:

- `Walkable`
- `Blocked`
- `Camp`
- `TentArea`
- `TrainingArea`
- `Forest`
- `Ocean`
- `Lake`
- `Infirmary`
- `CommanderArea`
- `WatchTowerVision`
- `SpawnArea`

`PointType` identifies semantic location markers:

- `CommanderChair`
- `Fire`
- `Basin`
- `WatchTower`
- `Bell`
- `BigAlarm`
- `Gate`
- `InfirmaryBed`
- `NurseStation`
- `SpawnPoint`
- `PatrolPoint`
- `RallyPoint`

## Pure Marker Data

`LayoutRootSettings`

- Holds global layout settings: `cellSize`, `gridSize`, `worldOrigin`, and debug toggles.
- Replaces the old Unreal root actor idea for now.

`ZoneMarker`

- Represents editable rectangular zones in pure data.
- Key fields: `type`, `faction`, `id`, `center`, `size`, `yawRadians`, `priority`.

`PointMarker`

- Represents authored semantic locations such as fire, basin, gate, chair, watchtower, and spawn point.
- Key fields: `type`, `faction`, `id`, `position`, `facingRadians`, `radius`, `slotCount`.

`WallMarker`

- Represents a thick 2D wall segment in pure data.
- Key fields: `localStart`, `localEnd`, `thickness`, `faction`.

`LayoutDraft`

- Holds root settings plus arrays of zones, authored locations, and walls.
- This is the current draft-level data container. Block 0B should turn this into validated/baked runtime layout data.

## Current Validation Stub

`summarizeLayout` counts zones, locations, and walls.

`formatBlock0AValidation` returns a human-readable Block 0A message with those counts. Real layout validation belongs to Block 0B.

## Current Visual Surface

`ModelerLayoutEditor.pyw` is the stable human-facing view for the project. It is meant to be the thing the desktop shortcut opens.

The editor currently supports:

- Direct dragging of zones, locations, and whole walls.
- Zone resize handles with opposite-corner anchoring.
- Location radius and facing handles.
- Wall endpoint handles.
- Exact numeric edits through the inspector.
- `Ctrl+Z` undo for layout and inspector changes.
- Mouse-wheel zoom and right-drag panning.
- Adjustable `Label Text Size` for on-map labels.
- Hover-first labels so the map stays quiet until you inspect a zone or location.
- Hover labels are attached to the main zone/location body, not the resize/rotate handles.
- Location labels rendered as decluttered callouts instead of raw overlapping text.
- Label badges, label text, and label connector lines raised above geometry so dense camp details stay readable while editing.
- Tent areas now read as grey, infirmaries as light/white, and training areas as orange in the saved layouts and editor defaults.
- A visible UI build stamp plus refresh-needed title state when the editor code on disk is newer than the running window.
- An in-app `Refresh App` action plus `Ctrl+R` to relaunch into the newest editor build without a manual close/reopen cycle.
- Explicit `Save Layout` button and `Ctrl+S` shortcut.
- Unsaved in-memory editing with a close prompt before discarding changes.
- Explicit save into `data/current_layout.json`.
- Camp sub-areas for tents, infirmaries, and training grounds.
- Background grass implied by absence of a specific zone, so the old grass hallway authoring zone has been removed.
- First Roman-side runtime sandbox with five prototype agents moving inside the authored Roman camp.
- In-editor `Play` / `Pause` plus time-speed control for compression and dilation while the scene keeps rendering at the normal UI cadence.
- Agent drag-and-drop without leaving the editor.
- Roman camp hard borders for the current prototype, with pathfinding intentionally deferred.
- `Freeze Layout` toggle so hover inspection can stay active while map handles, map selection drags, and layout edits are suppressed.
- Layout editing remains available while the simulation is running whenever `Freeze Layout` is off.
- Button focus hardened so pressing the spacebar toggles simulation instead of retriggering the last clicked button during map work.
- Explicit saves now persist the current camera zoom and pan, so refreshes and reopen cycles can return to the same authored view.

The important modeling rule here is that the viewer is now carrying simulation intent. If a camp gets an infirmary, tent footprint, or training area in the editor, that detail should be assumed available to future baking and runtime systems.

The important UI rule is that whole-scene readability wins over showing every label at once. The current default is hover-driven labels, so the authored map stays legible before we add moving agents on top.

The important interaction rule is that simulation and authoring are layered, not split into separate tools. Right now the Roman agent prototype lives directly on top of the editable map, and `Freeze Layout` acts as a temporary guardrail when the user wants to watch or drag agents without grabbing camp geometry.

For UI review work, prefer user-provided screenshots and background or headless checks before foreground launches whenever possible. That keeps the active user session undisturbed.

## Desktop Access

The intended non-technical entry point is the desktop shortcut:

- `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`

That shortcut targets the Python-backed local editor instead of a browser page or a copied launcher executable. This avoids the earlier failure mode where a moved executable could no longer find repo-relative files.

The launcher should also avoid reviving a stale editor window after code changes. If the script on disk is newer than the running editor process, launching from the shortcut should start a fresh instance so UI work is actually visible.

The desktop shortcut can also use a local override icon at `Build\desktop\ModelerDesktopIcon.ico` when that file exists. This keeps user-chosen shortcut art local without forcing a third-party asset into git.

If the shortcut ever disappears, recreate it with `tools/desktop/CreateCurrentSimulationShortcut.ps1`.

## Access Notes

The browser-based viewer has been retired on purpose. The intended user-facing entry point is now the native local editor window plus the desktop shortcut that opens it.

## Current Test Workflow

1. Open `ModelerLayoutEditor.pyw`.
2. Drag a zone, a location, and a wall endpoint.
3. Confirm location clicks are tight to the visible marker, especially for enlarged watchtowers.
4. Confirm dragging one zone corner keeps the opposite corner fixed instead of resizing symmetrically.
5. Confirm the map stays visually quiet until you hover a zone or location.
6. Confirm hovered labels appear above geometry instead of being clipped by nearby shapes.
7. Confirm `Ctrl+Z` reverses the last layout change.
8. Confirm mouse-wheel zoom and right-drag panning work.
9. Change `Label Text Size` and confirm the label rendering updates.
10. Confirm tent, infirmary, and training sub-areas exist inside each camp.
11. Confirm training areas render grey while tent areas and infirmaries render orange.
12. Confirm basin locations use blue centers, fire uses orange-red, watchtower uses purple, commander uses yellow, and gate locations stay transparent inside the white ring.
13. Confirm the old grass hallway zone is absent.
14. Click `Save Layout` or press `Ctrl+S`.
15. Confirm those edits appear in `data/current_layout.json`.
16. Close and reopen the editor without saving a fresh edit, and confirm unsaved session changes are not reloaded.
17. Click `Play` and confirm five Roman agents begin moving inside the Roman camp.
18. Change the simulation speed and confirm motion slows down or speeds up accordingly.
19. Drag an agent and confirm it remains inside the Roman camp bounds.
20. Toggle `Freeze Layout` on and confirm layout handles do not appear and map drags are blocked while hover inspection still works.
21. Toggle `Freeze Layout` off and confirm layout editing resumes immediately, even while the simulation is still running.
22. Press the spacebar after using toolbar buttons and confirm it toggles simulation instead of retriggering the previous button action.
23. Save the layout, refresh or reopen the editor, and confirm the camera returns to the saved zoom and pan.
24. Open `RunBlock0ASmoke.exe`.
25. The script initializes the Visual Studio C++ toolchain.
26. It compiles `tests/block0a_smoke.cpp` and `src/modeler/sim/LayoutMarkers.cpp`.
27. It runs the produced smoke test.
28. The smoke test creates one zone, one location, and one wall.
29. It asserts the summary counts and prints the Block 0A validation message.

## Verified

The native editor should open locally through the desktop shortcut or `ModelerLayoutEditor.pyw`. The Roman prototype agents should run directly inside that editor without a separate host app. The pure C++ Block 0A smoke test should still pass through `RunBlock0ASmoke.exe`. Keep both verified after each core change.

## Not Implemented Yet

Block 0B must add real validation and baked runtime layout data, still without Unreal dependencies.

Pathfinding, faction mirroring for Ottoman agents, combat, needs, perception, orders, final graphics, animation logic, persistent runtime saves, and Unreal integration still belong to later blocks.
