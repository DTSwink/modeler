#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Sim/SimTypes.h"
#include "SimZoneMarker.generated.h"

class UBoxComponent;

UCLASS()
class MODELER_API ASimZoneMarker : public AActor
{
	GENERATED_BODY()

public:
	ASimZoneMarker();

	virtual void OnConstruction(const FTransform& Transform) override;

#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

	UPROPERTY(VisibleAnywhere, Category = "Sim|Components")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, Category = "Sim|Components")
	TObjectPtr<UBoxComponent> PreviewBox;

	UPROPERTY(EditAnywhere, Category = "Sim")
	ESimZoneType ZoneType = ESimZoneType::Walkable;

	UPROPERTY(EditAnywhere, Category = "Sim")
	ESimFaction Faction = ESimFaction::Neutral;

	UPROPERTY(EditAnywhere, Category = "Sim")
	FName ZoneId;

	UPROPERTY(EditAnywhere, Category = "Sim", meta = (ClampMin = "1.0", UIMin = "100.0"))
	FVector2D Size2D = FVector2D(1000.0f, 1000.0f);

	UPROPERTY(EditAnywhere, Category = "Sim")
	int32 Priority = 0;

private:
	void UpdatePreview();
};
