// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "BackpackComponent.generated.h"

class UMVVM_Backpack;
class UInventoryModel;
struct FInventoryItem;

UCLASS(ClassGroup = (Custom), meta = (BlueprintSpawnableComponent))
class TEST_25D_API UBackpackComponent : public UActorComponent
{
	GENERATED_BODY()
public:	


	virtual void BeginPlay() override;

	UFUNCTION(BlueprintCallable)
	void PickupItem(const FInventoryItem& Item);

	UPROPERTY(BlueprintReadOnly)
	UInventoryModel* InventoryModel;

	UPROPERTY(BlueprintReadOnly)
	UMVVM_Backpack* InventoryVM;

};
