#include "Sim/EditorMarkers/SimLayoutRoot.h"

#include "EngineUtils.h"
#include "Sim/EditorMarkers/SimPointMarker.h"
#include "Sim/EditorMarkers/SimWallMarker.h"
#include "Sim/EditorMarkers/SimZoneMarker.h"

ASimLayoutRoot::ASimLayoutRoot()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;
}

void ASimLayoutRoot::ValidateLayout()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		UE_LOG(LogTemp, Warning, TEXT("[Sim Layout] ValidateLayout could not find a world."));
		return;
	}

	int32 ZoneCount = 0;
	int32 PointCount = 0;
	int32 WallCount = 0;

	for (TActorIterator<ASimZoneMarker> It(World); It; ++It)
	{
		++ZoneCount;
	}

	for (TActorIterator<ASimPointMarker> It(World); It; ++It)
	{
		++PointCount;
	}

	for (TActorIterator<ASimWallMarker> It(World); It; ++It)
	{
		++WallCount;
	}

	UE_LOG(LogTemp, Display, TEXT("[Sim Layout] Block 0A validation stub found %d zone marker(s), %d point marker(s), and %d wall marker(s). Full validation arrives in Block 0B."), ZoneCount, PointCount, WallCount);
}

void ASimLayoutRoot::BakeLayout()
{
	UE_LOG(LogTemp, Display, TEXT("[Sim Layout] BakeLayout is a Block 0A stub. Runtime layout baking will be implemented in Block 0B."));
}
