#include "Tests/InventoryTestGameplayEffects.h"

UInventoryTestDurationGameplayEffect::UInventoryTestDurationGameplayEffect()
{
	DurationPolicy = EGameplayEffectDurationType::HasDuration;
	DurationMagnitude = FScalableFloat(1.f);
}
