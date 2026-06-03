#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Sim/SimTypes.h"
#include "SimPointMarker.generated.h"

class UArrowComponent;
class USphereComponent;

UCLASS()
class MODELER_API ASimPointMarker : public AActor
{
	GENERATED_BODY()

public:
	ASimPointMarker();

	virtual void OnConstruction(const FTransform& Transform) override;

#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

	UPROPERTY(VisibleAnywhere, Category = "Sim|Components")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, Category = "Sim|Components")
	TObjectPtr<USphereComponent> PreviewSphere;

	UPROPERTY(VisibleAnywhere, Category = "Sim|Components")
	TObjectPtr<UArrowComponent> FacingArrow;

	UPROPERTY(EditAnywhere, Category = "Sim")
	ESimPointType PointType = ESimPointType::RallyPoint;

	UPROPERTY(EditAnywhere, Category = "Sim")
	ESimFaction Faction = ESimFaction::Neutral;

	UPROPERTY(EditAnywhere, Category = "Sim")
	FName PointId;

	UPROPERTY(EditAnywhere, Category = "Sim", meta = (ClampMin = "1.0", UIMin = "25.0"))
	float Radius = 100.0f;

	UPROPERTY(EditAnywhere, Category = "Sim", meta = (ClampMin = "0", UIMin = "0"))
	int32 SlotCount = 1;

private:
	void UpdatePreview();
};
