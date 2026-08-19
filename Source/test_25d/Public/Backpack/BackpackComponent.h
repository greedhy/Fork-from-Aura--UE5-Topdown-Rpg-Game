// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ReplicatedInventory.h"
#include "BackpackComponent.generated.h"

class UMVVM_Backpack;
class UItemDefinition;

UCLASS(ClassGroup = (Custom), meta = (BlueprintSpawnableComponent))
class TEST_25D_API UBackpackComponent : public UActorComponent
{
	GENERATED_BODY()
public:	
	UBackpackComponent();


	void Initialize();
	FInventoryAddResult TryAddItem(const UItemDefinition* Definition, int32 Quantity);
	bool SwapSlots(int32 IndexA, int32 IndexB);
	bool UseItemAt(int32 SlotIndex);

	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

	UPROPERTY(BlueprintReadOnly)
	UInventoryModel* InventoryModel;

	UPROPERTY(BlueprintReadOnly)
	UMVVM_Backpack* InventoryVM;

private:
	UFUNCTION()
	void OnRep_Inventory();

	bool HasServerAuthority() const;
	void InitializeReplicatedSlots();
	void SynchronizeReplicatedSlotsFromModel();

	UPROPERTY(ReplicatedUsing = OnRep_Inventory)
	FReplicatedInventoryList ReplicatedSlots;

	UPROPERTY(ReplicatedUsing = OnRep_Inventory)
	int32 Capacity = 16;

	UPROPERTY(ReplicatedUsing = OnRep_Inventory)
	int32 Revision = 0;
};
