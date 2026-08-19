#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WorldPickup.generated.h"

class UItemDefinition;

UCLASS(BlueprintType)
class TEST_25D_API AWorldPickup : public AActor
{
	GENERATED_BODY()

public:
	AWorldPickup();

	UItemDefinition* GetItemDefinition() const { return ItemDefinition; }
	int32 GetQuantity() const { return Quantity; }
	void SetItemDefinition(UItemDefinition* InItemDefinition);
	void SetQuantity(int32 InQuantity);
	bool ConsumeQuantity(int32 Amount);

	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

private:
	UPROPERTY(EditAnywhere, Replicated, Category = "Pickup")
	TObjectPtr<UItemDefinition> ItemDefinition;

	UPROPERTY(EditAnywhere, Replicated, Category = "Pickup", meta = (ClampMin = "0"))
	int32 Quantity = 1;
};
