// Fill out your copyright notice in the Description page of Project Settings.


#include "Game/MyGameInstance.h"

#include "Backpack/BackpackComponent.h"

UBackpackComponent* UMyGameInstance::GetBackpackComponent()
{
	if (!IsValid(BackpackComponent))
	{
		BackpackComponent = NewObject<UBackpackComponent>(this);
		BackpackComponent->Initialize();
	}
	return BackpackComponent;
}

