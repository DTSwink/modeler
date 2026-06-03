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

## Project Shape

Important files:

- `CurrentSimulation.html`: primary visual snapshot for the latest local sim state.
- `START_HERE.html`: rendered local launch page.
- `include/modeler/sim/SimTypes.h`: shared layout enums.
- `include/modeler/sim/LayoutMarkers.h`: engine-independent marker data.
- `src/modeler/sim/LayoutMarkers.cpp`: Block 0A marker summary/validation stub.
- `tests/block0a_smoke.cpp`: current smoke test.
- `tools/launchers/RunBlock0ASmoke.cpp`: Windows launcher source for the smoke test wrapper.
- `tools/desktop/CreateCurrentSimulationShortcut.ps1`: recreates the desktop shortcut if needed.
- `RunBlock0ASmoke.exe`: Windows wrapper that launches the smoke test script.
- `BuildAndTestCore.bat`: double-click build/test launcher.
- `StartModeler.bat`: opens the local start page.

Local convenience artifact:

- `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`: desktop shortcut that opens `CurrentSimulation.html`.

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

`CurrentSimulation.html` is the stable human-facing view for the project. It is meant to be the thing a desktop shortcut opens.

The page currently shows:

- A top-down visual preview of the intended first debug map.
- A count of current Block 0A structural elements.
- Honest status text explaining that the runtime agent sim is not built yet.

This page should evolve with the project. The shortcut should stay stable even as the underlying systems become more capable.

## Desktop Access

The intended non-technical entry point is the desktop shortcut:

- `C:\Users\singerie\Desktop\Modeler Current Simulation.lnk`

That shortcut targets `CurrentSimulation.html` directly instead of copying a launcher executable to the desktop. This avoids the earlier failure mode where a moved executable could no longer find repo-relative files such as `BuildAndTestCore.bat`.

If the shortcut ever disappears, recreate it with `tools/desktop/CreateCurrentSimulationShortcut.ps1`.

## Access Notes

Codex desktop local file links preview text files in the app editor. That means direct links to `.bat`, `.cmd`, `.ps1`, `.md`, or source files open the file instead of executing it.

Because of that:

- The preferred clickable sim entry point is `CurrentSimulation.html`.
- The preferred clickable tools page is `START_HERE.html`.
- The preferred runnable launcher is `RunBlock0ASmoke.exe`.
- `BuildAndTestCore.bat` remains the underlying script, but it is not the preferred chat-link target.

## Current Test Workflow

1. Open `RunBlock0ASmoke.exe`.
2. The script initializes the Visual Studio C++ toolchain.
3. It compiles `tests/block0a_smoke.cpp` and `src/modeler/sim/LayoutMarkers.cpp`.
4. It runs the produced smoke test.
5. The smoke test creates one zone, one point, and one wall.
6. It asserts the summary counts and prints the Block 0A validation message.

## Verified

The pure C++ Block 0A smoke test should pass locally through `RunBlock0ASmoke.exe`. `BuildAndTestCore.bat` remains the underlying script. Keep this verified after each core change.

## Not Implemented Yet

Block 0B must add real validation and baked runtime layout data, still without Unreal dependencies.

Do not add runtime AI, agents, pathfinding, combat, needs, perception, orders, final graphics, animation logic, or Unreal integration before their planned blocks.
