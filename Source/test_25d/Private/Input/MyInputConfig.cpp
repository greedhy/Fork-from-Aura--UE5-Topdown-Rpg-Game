// Fill out your copyright notice in the Description page of Project Settings.


#include "Input/MyInputConfig.h"

const UInputAction* UMyInputConfig::FindAbilityInputActionForTag(const FGameplayTag& InputTag, bool bLogNotFound) const
{
	for (const FMyInputAction& Action : AbilityInputActions)
	{
		if (Action .InputAction&&Action.InputTag == InputTag)
		{
			return Action.InputAction;
		}
	}
	if (bLogNotFound)
	{
		UE_LOG(LogTemp, Error, TEXT("Input action not found for tag: [%s] on InputConfig [%s]"), *InputTag.ToString(), *GetNameSafe(this));
	}
	return nullptr;
}
