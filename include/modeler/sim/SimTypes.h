#pragma once

#include <cstdint>

namespace modeler::sim
{
enum class Faction : std::uint8_t
{
	Neutral,
	Roman,
	Ottoman,
	Wildlife
};

enum class ZoneType : std::uint8_t
{
	Walkable,
	Blocked,
	Camp,
	TentArea,
	TrainingArea,
	Forest,
	Ocean,
	Lake,
	Infirmary,
	CommanderArea,
	WatchTowerVision,
	SpawnArea
};

enum class PointType : std::uint8_t
{
	CommanderChair,
	Fire,
	Basin,
	WatchTower,
	Bell,
	BigAlarm,
	Gate,
	InfirmaryBed,
	NurseStation,
	SpawnPoint,
	PatrolPoint,
	RallyPoint
};
}
