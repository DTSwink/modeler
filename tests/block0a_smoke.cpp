#include "modeler/sim/LayoutMarkers.h"

#include <cassert>
#include <iostream>

int main()
{
	modeler::sim::LayoutDraft draft;

	draft.zones.push_back({
		modeler::sim::ZoneType::Camp,
		modeler::sim::Faction::Roman,
		"roman_camp"
	});

	draft.points.push_back({
		modeler::sim::PointType::CommanderChair,
		modeler::sim::Faction::Roman,
		"roman_commander_chair"
	});

	draft.walls.push_back({});

	const modeler::sim::LayoutSummary summary = modeler::sim::summarizeLayout(draft);
	assert(summary.zoneCount == 1);
	assert(summary.pointCount == 1);
	assert(summary.wallCount == 1);

	std::cout << modeler::sim::formatBlock0AValidation(draft) << '\n';
	std::cout << "Block 0A pure core smoke test passed." << '\n';

	return 0;
}
