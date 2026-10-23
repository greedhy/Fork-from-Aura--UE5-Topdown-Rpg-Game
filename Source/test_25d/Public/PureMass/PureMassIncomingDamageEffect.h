#pragma once

#include "CoreMinimal.h"
#include "GameplayEffect.h"
#include "PureMassIncomingDamageEffect.generated.h"

/** Stable native definition for entity attacks delivered to an existing player's ASC. */
UCLASS()
class TEST_25D_API UPureMassIncomingDamageEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UPureMassIncomingDamageEffect();
    static FGameplayTag GetDamageTag();
};
