# Modeler

Engine-independent core for the Roman vs Ottoman 2D agent simulation.

This repo should not contain an Unreal project during the core-building phase. The simulation, layout model, validation, and debug tooling are built outside Unreal first. Unreal integration happens later through a dedicated adapter/hook layer.

## Start

Open `START_HERE.html` for the rendered local launch page.

Double-click `StartModeler.bat` to open that page from Windows.

Open `RunBlock0ASmoke.exe` to launch the current pure C++ smoke test without typing commands.

`BuildAndTestCore.bat` remains the underlying script if we need to inspect or change the build flow.

For the ongoing architecture record, read `Docs/SystemJournal.md`.

## Current Stop Point

Block 0A has been corrected to be engine-independent:

- Shared simulation layout enums.
- Plain C++ layout marker structs.
- Plain C++ layout draft container.
- Block 0A validation-summary stub.
- Smoke test for the pure core.

There is intentionally no `.uproject`, Unreal module, Unreal actor class, or generated Unreal build target in this repo now.

Do not continue to Block 0B until the engine-independent direction is approved.

## Test

1. Open `RunBlock0ASmoke.exe`.
2. Confirm the console reports marker counts.
3. Confirm it prints `Block 0A pure core smoke test passed.`
