# Modeler

Fresh Unreal Engine 5.7 C++ project for the Roman vs Ottoman 2D agent simulation.

## Start

Open `Modeler.uproject` to start the Unreal project.

On Windows, you can also double-click `StartModeler.bat`.

For the ongoing architecture record, read `Docs/SystemJournal.md`.

## Current Stop Point

Block 0A is implemented:

- `ASimLayoutRoot`
- `ASimZoneMarker`
- `ASimPointMarker`
- `ASimWallMarker`
- Shared simulation layout enums
- Editor-callable `ValidateLayout` and `BakeLayout` stubs
- Simple editor preview shapes for markers

Do not continue to Block 0B until marker placement has been tested and approved.

## Test

1. Open `Modeler.uproject`.
2. Create or open a level.
3. Place one `SimLayoutRoot`.
4. Place a few `SimZoneMarker`, `SimPointMarker`, and `SimWallMarker` actors.
5. Adjust marker properties in Details.
6. Click `ValidateLayout` on the root actor and confirm the Output Log reports marker counts.
7. Click `BakeLayout` and confirm the Output Log reports the Block 0A stub message.
