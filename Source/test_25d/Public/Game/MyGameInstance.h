// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "MyGameInstance.generated.h"

class UBackpackComponent;

/**
 * 
 */
UCLASS()
class TEST_25D_API UMyGameInstance : public UGameInstance
{
	GENERATED_BODY()
public:
	UBackpackComponent* GetBackpackComponent();

	UPROPERTY()
	FName PlayerStartTag = FName();

	UPROPERTY()
	FString LoadSlotName = FString();

	UPROPERTY()
	int32 LoadSlotIndex = 0;

private:
	UPROPERTY()
	TObjectPtr<UBackpackComponent> BackpackComponent;
};
