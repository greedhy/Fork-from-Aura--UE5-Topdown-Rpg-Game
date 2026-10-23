#include "Terrain/TerrainStatusEffects.h"
#include "AbilitySystem/MyAttributeSet.h"
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"

namespace TerrainTags
{
    UE_DEFINE_GAMEPLAY_TAG(Burning, "Debuff.Terrain.Burning");
    UE_DEFINE_GAMEPLAY_TAG(Frost, "Debuff.Terrain.Frost");
    UE_DEFINE_GAMEPLAY_TAG(Poison, "Debuff.Terrain.Poison");
    UE_DEFINE_GAMEPLAY_TAG(Entangled, "Debuff.Terrain.Entangled");
    UE_DEFINE_GAMEPLAY_TAG(Damage, "Data.Terrain.Damage");
}

namespace
{
void Configure(UGameplayEffect& Effect, UTargetTagsGameplayEffectComponent& Component, const FGameplayTag& Tag, bool bDamage)
{
    Effect.DurationPolicy = EGameplayEffectDurationType::Infinite;
    FInheritedTagContainer Tags;
    Tags.AddTag(Tag);
    Component.SetAndApplyTargetTagChanges(Tags);
    if (bDamage)
    {
        Effect.Period = FScalableFloat(1.f);
        Effect.bExecutePeriodicEffectOnApplication = false;
        FSetByCallerFloat Damage;
        Damage.DataTag = TerrainTags::Damage;
        FGameplayModifierInfo Modifier;
        Modifier.Attribute = UMyAttributeSet::GetIncomingDamageAttribute();
        Modifier.ModifierOp = EGameplayModOp::Additive;
        Modifier.ModifierMagnitude = FGameplayEffectModifierMagnitude(Damage);
        Effect.Modifiers.Add(Modifier);
    }
}
}
UTerrainBurnEffect::UTerrainBurnEffect()
{
    auto* Tags = CreateDefaultSubobject<UTargetTagsGameplayEffectComponent>(TEXT("TerrainTags"));
    GEComponents.Add(Tags);
    Configure(*this, *Tags, TerrainTags::Burning, true);
}
UTerrainFrostEffect::UTerrainFrostEffect()
{
    auto* Tags = CreateDefaultSubobject<UTargetTagsGameplayEffectComponent>(TEXT("TerrainTags"));
    GEComponents.Add(Tags);
    Configure(*this, *Tags, TerrainTags::Frost, false);
}
UTerrainPoisonEffect::UTerrainPoisonEffect()
{
    auto* Tags = CreateDefaultSubobject<UTargetTagsGameplayEffectComponent>(TEXT("TerrainTags"));
    GEComponents.Add(Tags);
    Configure(*this, *Tags, TerrainTags::Poison, true);
}
UTerrainEntangleEffect::UTerrainEntangleEffect()
{
    auto* Tags = CreateDefaultSubobject<UTargetTagsGameplayEffectComponent>(TEXT("TerrainTags"));
    GEComponents.Add(Tags);
    Configure(*this, *Tags, TerrainTags::Entangled, false);
}
