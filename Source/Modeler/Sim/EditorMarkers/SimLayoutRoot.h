#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SimLayoutRoot.generated.h"

UCLASS()
class MODELER_API ASimLayoutRoot : public AActor
{
	GENERATED_BODY()

public:
	ASimLayoutRoot();

	UPROPERTY(VisibleAnywhere, Category = "Sim|Components")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(EditAnywhere, Category = "Sim|Grid")
	float CellSize = 100.0f;

	UPROPERTY(EditAnywhere, Category = "Sim|Grid")
	FIntPoint GridSize = FIntPoint(240, 80);

	UPROPERTY(EditAnywhere, Category = "Sim|Origin")
	FVector WorldOrigin = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, Category = "Sim|Debug")
	bool bDrawLayout = true;

	UPROPERTY(EditAnywhere, Category = "Sim|Debug")
	bool bDrawGrid = true;

	UPROPERTY(EditAnywhere, Category = "Sim|Debug")
	bool bDrawLabels = true;

	UFUNCTION(CallInEditor, Category = "Sim|Layout")
	void ValidateLayout();

	UFUNCTION(CallInEditor, Category = "Sim|Layout")
	void BakeLayout();
};
