#pragma once

#include "CoreMinimal.h"
#include "SimTypes.generated.h"

UENUM(BlueprintType)
enum class ESimFaction : uint8
{
	Neutral,
	Roman,
	Ottoman,
	Wildlife
};

UENUM(BlueprintType)
enum class ESimZoneType : uint8
{
	Walkable,
	Blocked,
	Camp,
	Forest,
	Ocean,
	Lake,
	Infirmary,
	CommanderArea,
	WatchTowerVision,
	SpawnArea
};

UENUM(BlueprintType)
enum class ESimPointType : uint8
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
