#include "PureMass/PureMassIncomingDamageEffect.h"
#include "AbilitySystem/MyAttributeSet.h"
#include "NativeGameplayTags.h"

// Reuse the existing project tag. Native registration makes it available even when the CDO
// is constructed before the asset manager initializes FMyGameplayTags.
UE_DEFINE_GAMEPLAY_TAG_STATIC(PureMassPhysicalDamageTag, "Damage.Physics");

FGameplayTag UPureMassIncomingDamageEffect::GetDamageTag()
{
    return PureMassPhysicalDamageTag;
}

UPureMassIncomingDamageEffect::UPureMassIncomingDamageEffect()
{
    DurationPolicy = EGameplayEffectDurationType::Instant;
    FSetByCallerFloat Damage;
    Damage.DataTag = GetDamageTag();
    FGameplayModifierInfo& Modifier = Modifiers.AddDefaulted_GetRef();
    Modifier.Attribute = UMyAttributeSet::GetIncomingDamageAttribute();
    Modifier.ModifierOp = EGameplayModOp::Additive;
    Modifier.ModifierMagnitude = FGameplayEffectModifierMagnitude(Damage);
}
