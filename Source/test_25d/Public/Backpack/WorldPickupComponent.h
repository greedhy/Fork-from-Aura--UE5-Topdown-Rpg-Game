#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Backpack/ItemDefinition.h"
#include "WorldPickupComponent.generated.h"

class UBackpackItemDefinitions;
class UPrimitiveComponent;
class AMyPlayerState;

UCLASS(ClassGroup=(Backpack), meta=(BlueprintSpawnableComponent))
class TEST_25D_API UWorldPickupComponent : public UActorComponent
{
	GENERATED_BODY()
public:
	UWorldPickupComponent();
	virtual void BeginPlay() override;
	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

	bool TryPickup(AMyPlayerState* PlayerState);
	/** Ensures pickup Actors spawned by either C++ or Blueprint are visible to all clients. */
	static void ConfigureOwnerForNetworkedPickup(AActor* PickupActor);
	void ConfigurePickup(const FPrimaryAssetId& InItemDefinitionId, int32 InQuantity, bool bForceInteract);
	EPickupMode GetPickupMode() const { return bForceInteract ? EPickupMode::Interact : PickupMode; }
	const FPrimaryAssetId& GetItemDefinitionId() const { return ItemDefinitionId; }
	int32 GetQuantity() const { return Quantity; }

	UPROPERTY(EditAnywhere, Category="Pickup")
	TObjectPtr<UBackpackItemDefinitions> ItemDefinitions;
	UPROPERTY(EditAnywhere, Replicated, Category="Pickup")
	FPrimaryAssetId ItemDefinitionId;
	UPROPERTY(EditAnywhere, Replicated, Category="Pickup", meta=(ClampMin="1"))
	int32 Quantity = 1;

private:
	UFUNCTION()
	void HandleOwnerOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
	UFUNCTION()
	void HandleOwnerEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComponent, int32 OtherBodyIndex);
	void ResolveDefinition();
	UPROPERTY(Replicated)
	EPickupMode PickupMode = EPickupMode::Interact;
	UPROPERTY(Replicated)
	bool bForceInteract = false;
};
