#include "Tests/EquipmentTestEffects.h"
#include "AbilitySystem/MyAttributeSet.h"
namespace
{
void Add(UGameplayEffect& GE, FGameplayAttribute Attribute, float Value)
{
 FGameplayModifierInfo M; M.Attribute = Attribute; M.ModifierOp = EGameplayModOp::Additive;
 M.EvaluationChannelSettings.SetEvaluationChannel(EGameplayModEvaluationChannel::Channel1);
 M.ModifierMagnitude = FScalableFloat(Value); GE.Modifiers.Add(M);
}
}
UEquipmentTestArmor::UEquipmentTestArmor() { Add(*this, UMyAttributeSet::GetArmorAttribute(), 5.f); }
UEquipmentTestArmorSeven::UEquipmentTestArmorSeven() { Add(*this, UMyAttributeSet::GetArmorAttribute(), 7.f); }
UEquipmentTestHealth::UEquipmentTestHealth() { Add(*this, UMyAttributeSet::GetMaxHealthAttribute(), 50.f); }
