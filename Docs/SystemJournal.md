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

Block 0A is implemented and must be tested before Block 0B begins.

Block 0A means the project only contains editable layout marker actors and shared marker enums. It does not yet contain baked layout data, runtime simulation, debug visualization, agents, possession, input, movement, or root-motion prediction.

## Core Principle

The player is never a special simulation entity. Later, player control should be represented by assigning an ordinary agent a `PlayerInput` brain. The agent keeps its normal faction, role, position, state, and capabilities.

## Project Shape

The project is a fresh Unreal Engine 5.7 C++ project named `Modeler`.

Important files:

- `Modeler.uproject`: Unreal project entry point.
- `Source/Modeler/Modeler.Build.cs`: runtime module rules.
- `Source/Modeler/Sim/SimTypes.h`: shared layout enums.
- `Source/Modeler/Sim/EditorMarkers/`: Block 0A marker actors.

Generated folders such as `Binaries`, `Intermediate`, `Saved`, and `DerivedDataCache` are ignored by git.

## Block 0A Components

`ESimFaction` identifies semantic ownership:

- `Neutral`
- `Roman`
- `Ottoman`
- `Wildlife`

`ESimZoneType` identifies rectangular area semantics:

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

`ESimPointType` identifies semantic point markers:

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

## Marker Actors

`ASimLayoutRoot`

- Place one per map.
- Owns global layout settings such as `CellSize`, `GridSize`, `WorldOrigin`, and debug toggles.
- Has editor-callable `ValidateLayout` and `BakeLayout` buttons.
- In Block 0A, `ValidateLayout` only counts marker actors and prints a summary.
- In Block 0A, `BakeLayout` only prints a stub message.

`ASimZoneMarker`

- Represents editable rectangular zones.
- Key properties: `ZoneType`, `Faction`, `ZoneId`, `Size2D`, `Priority`.
- Uses a non-colliding `UBoxComponent` preview.
- Preview color changes by zone type.

`ASimPointMarker`

- Represents semantic points such as fire, basin, gate, chair, watchtower, and spawn point.
- Key properties: `PointType`, `Faction`, `PointId`, `Radius`, `SlotCount`.
- Uses a non-colliding `USphereComponent` preview and a facing arrow.
- Preview color changes by point type.

`ASimWallMarker`

- Represents a thick 2D wall segment.
- Key properties: `LocalStart`, `LocalEnd`, `Thickness`, `Faction`.
- Uses a non-colliding `UBoxComponent` preview aligned between start and end.

## Editor Workflow For Current Block

1. Open `Modeler.uproject`.
2. Create or open a level.
3. Place one `SimLayoutRoot`.
4. Place zones, points, and walls.
5. Edit marker properties in Details.
6. Select the root actor and run `ValidateLayout`.
7. Confirm the Output Log reports marker counts.
8. Run `BakeLayout`.
9. Confirm the Output Log reports the Block 0A bake stub.

## Verified

The `ModelerEditor Win64 Development` target built successfully with Unreal Engine 5.7.

## Not Implemented Yet

Block 0B must add baked runtime layout data and real validation. Do not add runtime AI, agents, pathfinding, combat, needs, perception, orders, final graphics, or animation logic before their planned blocks.
