#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Sim/SimTypes.h"
#include "SimWallMarker.generated.h"

class UBoxComponent;

UCLASS()
class MODELER_API ASimWallMarker : public AActor
{
	GENERATED_BODY()

public:
	ASimWallMarker();

	virtual void OnConstruction(const FTransform& Transform) override;

#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

	UPROPERTY(VisibleAnywhere, Category = "Sim|Components")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, Category = "Sim|Components")
	TObjectPtr<UBoxComponent> PreviewBox;

	UPROPERTY(EditAnywhere, Category = "Sim")
	FVector2D LocalStart = FVector2D(-500.0f, 0.0f);

	UPROPERTY(EditAnywhere, Category = "Sim")
	FVector2D LocalEnd = FVector2D(500.0f, 0.0f);

	UPROPERTY(EditAnywhere, Category = "Sim", meta = (ClampMin = "1.0", UIMin = "25.0"))
	float Thickness = 100.0f;

	UPROPERTY(EditAnywhere, Category = "Sim")
	ESimFaction Faction = ESimFaction::Neutral;

private:
	void UpdatePreview();
};
