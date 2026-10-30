#include "Equipment/EquipmentGameplayEffect.h"
#include "AbilitySystem/MyAttributeSet.h"
#include "GameplayAbilitiesDeveloperSettings.h"
#include "NativeGameplayTags.h"
#include "Equipment/EquipmentGenerator.h"
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_EquipmentArmor, "Equipment.Stat.Armor");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_EquipmentMaxHealth, "Equipment.Stat.MaxHealth");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_EquipmentMaxMana, "Equipment.Stat.MaxMana");
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"

UEquipmentGameplayEffect::UEquipmentGameplayEffect()
{
 DurationPolicy = EGameplayEffectDurationType::Infinite;
 Period = FScalableFloat(0.f);
 StackingType = EGameplayEffectStackingType::None;
}

bool UEquipmentGameplayEffect::IsSafeEquipmentEffect(float Level, bool bAllowRolled) const
{
 if (!GetDefault<UGameplayAbilitiesDeveloperSettings>()->bAllowGameplayModEvaluationChannels || !FMath::IsFinite(Level) || Level < 1.f || DurationPolicy != EGameplayEffectDurationType::Infinite ||
     Period.GetValueAtLevel(Level) != 0.f || GetStackingType() != EGameplayEffectStackingType::None || !Executions.IsEmpty()) return false;
 for (const auto& Component : GEComponents)
  if (Component && Component->GetClass() != UTargetTagsGameplayEffectComponent::StaticClass()) return false;
 if (bAllowRolled && Modifiers.Num() != 3) return false;
 TSet<FGameplayAttribute> SeenAttributes;
 for (const auto& Modifier : Modifiers)
 {
  if (bAllowRolled && SeenAttributes.Contains(Modifier.Attribute)) return false;
  SeenAttributes.Add(Modifier.Attribute);
  float Value = 0.f;
  if (!Modifier.Attribute.IsValid() || Modifier.Attribute.GetAttributeSetClass() != UMyAttributeSet::StaticClass() ||
      Modifier.Attribute == UMyAttributeSet::GetHealthAttribute() || Modifier.Attribute == UMyAttributeSet::GetManaAttribute() ||
      Modifier.Attribute == UMyAttributeSet::GetIncomingDamageAttribute() || Modifier.Attribute == UMyAttributeSet::GetIncomingXPAttribute() ||
      Modifier.EvaluationChannelSettings.GetEvaluationChannel() != EGameplayModEvaluationChannel::Channel1 ||
      Modifier.ModifierOp != EGameplayModOp::Additive) return false;
  if (bAllowRolled)
  {
   if (Modifier.ModifierMagnitude.GetMagnitudeCalculationType() != EGameplayEffectMagnitudeCalculation::SetByCaller) return false;
   const auto Tag = Modifier.ModifierMagnitude.GetSetByCallerFloat().DataTag;
   const bool bMatches = (Tag == TAG_EquipmentArmor && Modifier.Attribute == UMyAttributeSet::GetArmorAttribute()) ||
    (Tag == TAG_EquipmentMaxHealth && Modifier.Attribute == UMyAttributeSet::GetMaxHealthAttribute()) ||
    (Tag == TAG_EquipmentMaxMana && Modifier.Attribute == UMyAttributeSet::GetMaxManaAttribute());
   if (!bMatches) return false;
  }
  else if (!Modifier.ModifierMagnitude.GetStaticMagnitudeIfPossible(Level, Value) || !FMath::IsFinite(Value)) return false;
 }
 return true;
}

URandomEquipmentGameplayEffect::URandomEquipmentGameplayEffect()
{
 const FGameplayAttribute Attributes[] = {UMyAttributeSet::GetArmorAttribute(), UMyAttributeSet::GetMaxHealthAttribute(), UMyAttributeSet::GetMaxManaAttribute()};
 const FGameplayTag Tags[] = {TAG_EquipmentArmor, TAG_EquipmentMaxHealth, TAG_EquipmentMaxMana};
 for (int32 I=0; I<3; ++I)
 {
  FGameplayModifierInfo M; M.Attribute=Attributes[I]; M.ModifierOp=EGameplayModOp::Additive;
  M.EvaluationChannelSettings.SetEvaluationChannel(EGameplayModEvaluationChannel::Channel1);
  FSetByCallerFloat Magnitude; Magnitude.DataTag=Tags[I]; M.ModifierMagnitude=FGameplayEffectModifierMagnitude(Magnitude);
  Modifiers.Add(M);
 }
}
