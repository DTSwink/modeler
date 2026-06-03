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

Block 0A has been corrected and is awaiting approval.

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

`PointType` identifies semantic point markers:

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

- Represents semantic points such as fire, basin, gate, chair, watchtower, and spawn point.
- Key fields: `type`, `faction`, `id`, `position`, `facingRadians`, `radius`, `slotCount`.

`WallMarker`

- Represents a thick 2D wall segment in pure data.
- Key fields: `localStart`, `localEnd`, `thickness`, `faction`.

`LayoutDraft`

- Holds root settings plus arrays of zones, points, and walls.
- This is the current draft-level data container. Block 0B should turn this into validated/baked runtime layout data.

## Current Validation Stub

`summarizeLayout` counts zones, points, and walls.

`formatBlock0AValidation` returns a human-readable Block 0A message with those counts. Real layout validation belongs to Block 0B.

## Current Visual Surface

`ModelerLayoutEditor.pyw` is the stable human-facing view for the project. It is meant to be the thing the desktop shortcut opens.

The editor currently supports:

- Direct dragging of zones, points, and whole walls.
- Zone resize handles with opposite-corner anchoring.
- Point radius and facing handles.
- Wall endpoint handles.
- Exact numeric edits through the inspector.
- `Ctrl+Z` undo for layout and inspector changes.
- Mouse-wheel zoom and right-drag panning.
- Adjustable `Label Text Size` for on-map labels.
- Adaptive label density so full-scene views show major geography first and dense local detail later.
- Point labels rendered as decluttered callouts instead of raw overlapping text.
- Label badges, label text, and label connector lines raised above geometry so dense camp details stay readable while editing.
- A visible UI build stamp plus restart-needed title state when the editor code on disk is newer than the running window.
- Explicit `Save Layout` button and `Ctrl+S` shortcut.
- Unsaved in-memory editing with a close prompt before discarding changes.
- Explicit save into `data/current_layout.json`.
- Camp sub-areas for tents, infirmaries, and training grounds.
- Background grass implied by absence of a specific zone, so the old grass hallway authoring zone has been removed.

The important modeling rule here is that the viewer is now carrying simulation intent. If a camp gets an infirmary, tent footprint, or training area in the editor, that detail should be assumed available to future baking and runtime systems.

The important UI rule is that whole-scene readability wins over showing every label at once. Smaller camp-internal labels can hide until selection or zoom if that keeps the authored scene understandable.

For UI review work, prefer user-provided screenshots and background or headless checks before foreground launches whenever possible. That keeps the active user session undisturbed.

## Desktop Access

The intended non-technical entry point is the desktop shortcut:

- `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`

That shortcut targets the Python-backed local editor instead of a browser page or a copied launcher executable. This avoids the earlier failure mode where a moved executable could no longer find repo-relative files.

The launcher should also avoid reviving a stale editor window after code changes. If the script on disk is newer than the running editor process, launching from the shortcut should start a fresh instance so UI work is actually visible.

If the shortcut ever disappears, recreate it with `tools/desktop/CreateCurrentSimulationShortcut.ps1`.

## Access Notes

The browser-based viewer has been retired on purpose. The intended user-facing entry point is now the native local editor window plus the desktop shortcut that opens it.

## Current Test Workflow

1. Open `ModelerLayoutEditor.pyw`.
2. Drag a zone, a point, and a wall endpoint.
3. Confirm point clicks are tight to the visible marker, especially for enlarged watchtowers.
4. Confirm dragging one zone corner keeps the opposite corner fixed instead of resizing symmetrically.
5. Confirm the full-scene view keeps major region labels readable without camp internals turning into a text pile.
6. Confirm `Label Density` changes label visibility as expected.
7. Confirm `Ctrl+Z` reverses the last layout change.
8. Confirm mouse-wheel zoom and right-drag panning work.
9. Change `Label Text Size` and confirm the label rendering updates.
10. Confirm tent, infirmary, and training sub-areas exist inside each camp.
11. Confirm the old grass hallway zone is absent.
12. Click `Save Layout` or press `Ctrl+S`.
13. Confirm those edits appear in `data/current_layout.json`.
14. Close and reopen the editor without saving a fresh edit, and confirm unsaved session changes are not reloaded.
15. Open `RunBlock0ASmoke.exe`.
16. The script initializes the Visual Studio C++ toolchain.
17. It compiles `tests/block0a_smoke.cpp` and `src/modeler/sim/LayoutMarkers.cpp`.
18. It runs the produced smoke test.
19. The smoke test creates one zone, one point, and one wall.
20. It asserts the summary counts and prints the Block 0A validation message.

## Verified

The native editor should open locally through the desktop shortcut or `ModelerLayoutEditor.pyw`. The pure C++ Block 0A smoke test should still pass through `RunBlock0ASmoke.exe`. Keep both verified after each core change.

## Not Implemented Yet

Block 0B must add real validation and baked runtime layout data, still without Unreal dependencies.

Do not add runtime AI, agents, pathfinding, combat, needs, perception, orders, final graphics, animation logic, or Unreal integration before their planned blocks.
