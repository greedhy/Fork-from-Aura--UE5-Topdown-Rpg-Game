#pragma once

#include "CoreMinimal.h"
#include "GameplayEffect.h"
#include "NativeGameplayTags.h"
#include "TerrainStatusEffects.generated.h"

namespace TerrainTags
{
    TEST_25D_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Burning);
    TEST_25D_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Frost);
    TEST_25D_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Poison);
    TEST_25D_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Entangled);
    TEST_25D_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Damage);
}

UCLASS()
class TEST_25D_API UTerrainBurnEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UTerrainBurnEffect();
};
UCLASS()
class TEST_25D_API UTerrainFrostEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UTerrainFrostEffect();
};
UCLASS()
class TEST_25D_API UTerrainPoisonEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UTerrainPoisonEffect();
};
UCLASS()
class TEST_25D_API UTerrainEntangleEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UTerrainEntangleEffect();
};
