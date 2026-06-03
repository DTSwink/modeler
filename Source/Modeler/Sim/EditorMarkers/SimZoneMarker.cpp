#include "Sim/EditorMarkers/SimZoneMarker.h"

#include "Components/BoxComponent.h"

ASimZoneMarker::ASimZoneMarker()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	PreviewBox = CreateDefaultSubobject<UBoxComponent>(TEXT("PreviewBox"));
	PreviewBox->SetupAttachment(SceneRoot);
	PreviewBox->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PreviewBox->SetCanEverAffectNavigation(false);
	PreviewBox->ShapeColor = FColor::Green;

	UpdatePreview();
}

void ASimZoneMarker::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	UpdatePreview();
}

#if WITH_EDITOR
void ASimZoneMarker::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);
	UpdatePreview();
}
#endif

void ASimZoneMarker::UpdatePreview()
{
	if (!PreviewBox)
	{
		return;
	}

	const FVector Extent(
		FMath::Max(1.0f, Size2D.X * 0.5f),
		FMath::Max(1.0f, Size2D.Y * 0.5f),
		25.0f);

	PreviewBox->SetBoxExtent(Extent);

	switch (ZoneType)
	{
	case ESimZoneType::Blocked:
		PreviewBox->ShapeColor = FColor::Silver;
		break;
	case ESimZoneType::Camp:
		PreviewBox->ShapeColor = FColor::Yellow;
		break;
	case ESimZoneType::Forest:
		PreviewBox->ShapeColor = FColor::Green;
		break;
	case ESimZoneType::Ocean:
	case ESimZoneType::Lake:
		PreviewBox->ShapeColor = FColor::Blue;
		break;
	case ESimZoneType::SpawnArea:
		PreviewBox->ShapeColor = FColor::Cyan;
		break;
	default:
		PreviewBox->ShapeColor = FColor::White;
		break;
	}
}
