#pragma once

#include "CoreMinimal.h"
#include "GameplayEffect.h"
#include "InventoryTestGameplayEffects.generated.h"

UCLASS()
class UInventoryTestInstantGameplayEffect : public UGameplayEffect
{
	GENERATED_BODY()
};

UCLASS()
class UInventoryTestDurationGameplayEffect : public UGameplayEffect
{
	GENERATED_BODY()

public:
	UInventoryTestDurationGameplayEffect();
};
