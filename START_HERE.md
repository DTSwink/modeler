# Start Here

## Open The Local Entry Point

Double-click `StartModeler.bat` to open this page.

## Run The Current Module

Double-click `BuildAndTestCore.bat` to compile and run the current engine-independent smoke test.

## Current Work Gate

The repo is intentionally stopped at Block 0A. The current task is to approve the engine-independent foundation before Block 0B begins.

## Main References

- `README.md`: quick project status and test checklist.
- `Docs/SystemJournal.md`: living journal of how the system works.
- `include/modeler/sim/`: public pure C++ sim headers.
- `src/modeler/sim/`: pure C++ sim implementation.
- `tests/block0a_smoke.cpp`: current smoke test.
- `BuildAndTestCore.bat`: double-click build/test launcher.

## Important Boundary

There is no Unreal project here right now. Unreal is only a future integration target.
