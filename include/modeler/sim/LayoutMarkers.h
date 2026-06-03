#pragma once

#include "modeler/sim/SimTypes.h"

#include <cstddef>
#include <string>
#include <vector>

namespace modeler::sim
{
struct Vec2
{
	double x = 0.0;
	double y = 0.0;
};

struct Int2
{
	int x = 0;
	int y = 0;
};

struct LayoutRootSettings
{
	double cellSize = 100.0;
	Int2 gridSize = { 240, 80 };
	Vec2 worldOrigin = {};
	bool drawLayout = true;
	bool drawGrid = true;
	bool drawLabels = true;
};

struct ZoneMarker
{
	ZoneType type = ZoneType::Walkable;
	Faction faction = Faction::Neutral;
	std::string id;
	Vec2 center = {};
	Vec2 size = { 1000.0, 1000.0 };
	double yawRadians = 0.0;
	int priority = 0;
};

struct PointMarker
{
	// Editor-facing "locations" are stored as PointMarker entries for now.
	PointType type = PointType::RallyPoint;
	Faction faction = Faction::Neutral;
	std::string id;
	Vec2 position = {};
	double facingRadians = 0.0;
	double radius = 100.0;
	int slotCount = 1;
};

struct WallMarker
{
	Vec2 localStart = { -500.0, 0.0 };
	Vec2 localEnd = { 500.0, 0.0 };
	double thickness = 100.0;
	Faction faction = Faction::Neutral;
};

struct LayoutDraft
{
	LayoutRootSettings root;
	std::vector<ZoneMarker> zones;
	// These point markers are authored locations in the top-down editor.
	std::vector<PointMarker> points;
	std::vector<WallMarker> walls;
};

struct LayoutSummary
{
	std::size_t zoneCount = 0;
	std::size_t pointCount = 0;
	std::size_t wallCount = 0;
};

LayoutSummary summarizeLayout(const LayoutDraft& draft);
std::string formatBlock0AValidation(const LayoutDraft& draft);
}
