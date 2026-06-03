#include "Sim/EditorMarkers/SimPointMarker.h"

#include "Components/ArrowComponent.h"
#include "Components/SphereComponent.h"

ASimPointMarker::ASimPointMarker()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	PreviewSphere = CreateDefaultSubobject<USphereComponent>(TEXT("PreviewSphere"));
	PreviewSphere->SetupAttachment(SceneRoot);
	PreviewSphere->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PreviewSphere->SetCanEverAffectNavigation(false);
	PreviewSphere->ShapeColor = FColor::Cyan;

	FacingArrow = CreateDefaultSubobject<UArrowComponent>(TEXT("FacingArrow"));
	FacingArrow->SetupAttachment(SceneRoot);
	FacingArrow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	FacingArrow->SetCanEverAffectNavigation(false);
	FacingArrow->ArrowSize = 1.5f;

	UpdatePreview();
}

void ASimPointMarker::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	UpdatePreview();
}

#if WITH_EDITOR
void ASimPointMarker::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);
	UpdatePreview();
}
#endif

void ASimPointMarker::UpdatePreview()
{
	if (!PreviewSphere || !FacingArrow)
	{
		return;
	}

	PreviewSphere->SetSphereRadius(FMath::Max(1.0f, Radius));

	switch (PointType)
	{
	case ESimPointType::Fire:
		PreviewSphere->ShapeColor = FColor::Orange;
		break;
	case ESimPointType::Basin:
		PreviewSphere->ShapeColor = FColor::Cyan;
		break;
	case ESimPointType::CommanderChair:
		PreviewSphere->ShapeColor = FColor::Purple;
		break;
	case ESimPointType::Gate:
		PreviewSphere->ShapeColor = FColor::Green;
		break;
	case ESimPointType::WatchTower:
		PreviewSphere->ShapeColor = FColor::Magenta;
		break;
	case ESimPointType::SpawnPoint:
		PreviewSphere->ShapeColor = FColor::Yellow;
		break;
	default:
		PreviewSphere->ShapeColor = FColor::White;
		break;
	}
}
