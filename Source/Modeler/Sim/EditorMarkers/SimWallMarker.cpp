#include "Sim/EditorMarkers/SimWallMarker.h"

#include "Components/BoxComponent.h"

ASimWallMarker::ASimWallMarker()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	RootComponent = SceneRoot;

	PreviewBox = CreateDefaultSubobject<UBoxComponent>(TEXT("PreviewBox"));
	PreviewBox->SetupAttachment(SceneRoot);
	PreviewBox->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PreviewBox->SetCanEverAffectNavigation(false);
	PreviewBox->ShapeColor = FColor::Silver;

	UpdatePreview();
}

void ASimWallMarker::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	UpdatePreview();
}

#if WITH_EDITOR
void ASimWallMarker::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	Super::PostEditChangeProperty(PropertyChangedEvent);
	UpdatePreview();
}
#endif

void ASimWallMarker::UpdatePreview()
{
	if (!PreviewBox)
	{
		return;
	}

	const FVector2D Delta = LocalEnd - LocalStart;
	const float Length = FMath::Max(1.0f, Delta.Size());
	const FVector2D Center = (LocalStart + LocalEnd) * 0.5f;
	const float YawDegrees = FMath::RadiansToDegrees(FMath::Atan2(Delta.Y, Delta.X));

	PreviewBox->SetRelativeLocation(FVector(Center.X, Center.Y, 0.0f));
	PreviewBox->SetRelativeRotation(FRotator(0.0f, YawDegrees, 0.0f));
	PreviewBox->SetBoxExtent(FVector(Length * 0.5f, FMath::Max(1.0f, Thickness * 0.5f), 50.0f));
}
