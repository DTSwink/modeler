#include "modeler/sim/LayoutMarkers.h"

#include <sstream>

namespace modeler::sim
{
LayoutSummary summarizeLayout(const LayoutDraft& draft)
{
	return {
		draft.zones.size(),
		draft.points.size(),
		draft.walls.size()
	};
}

std::string formatBlock0AValidation(const LayoutDraft& draft)
{
	const LayoutSummary summary = summarizeLayout(draft);

	std::ostringstream out;
	out << "[Sim Layout] Block 0A validation stub found "
		<< summary.zoneCount << " zone marker(s), "
		<< summary.pointCount << " point marker(s), and "
		<< summary.wallCount << " wall marker(s). "
		<< "Full validation arrives in Block 0B.";

	return out.str();
}
}
