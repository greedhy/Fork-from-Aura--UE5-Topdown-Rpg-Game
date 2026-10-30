// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ReplicatedInventory.h"
#include "BackpackComponent.generated.h"

class UMVVM_Backpack;
class UItemDefinition;
class UBackpackItemDefinitions;
class APawn;
class AMyPlayerController;

DECLARE_MULTICAST_DELEGATE(FOnBackpackStateChanged);

UCLASS(ClassGroup = (Custom), meta = (BlueprintSpawnableComponent))
class TEST_25D_API UBackpackComponent : public UActorComponent
{
	GENERATED_BODY()
public:	
	UBackpackComponent();


	void Initialize();
	FInventoryAddResult TryAddItem(const UItemDefinition* Definition, int32 Quantity);
	FInventoryAddResult TryAddItem(const FPrimaryAssetId& ItemDefinitionId, int32 Quantity);
	bool TryAddExistingItem(const FPrimaryAssetId& Id, const FGuid& InstanceId, const FEquipmentRollData& RollData = FEquipmentRollData());
	void SetItemDefinitions(UBackpackItemDefinitions* InItemDefinitions);
	static void ConfigureSpawnedPickupActor(AActor* PickupActor);
	bool DropWholeStack(int32 SlotIndex, const FVector& SpawnLocation);
	bool SwapSlots(int32 IndexA, int32 IndexB);
	bool TryUseItemForPawn(int32 SlotIndex, APawn* Pawn);
	bool SetCapacity(int32 NewCapacity);
	bool RestorePersistentSlots(const TArray<FReplicatedInventorySlot>& SavedSlots, int32 SavedCapacity, int32 SavedRevision);

	const UInventoryModel* GetInventoryModel() const { return InventoryModel; }
	const FReplicatedInventoryList& GetReplicatedSlots() const { return ReplicatedSlots; }
	int32 GetCapacity() const { return Capacity; }
	int32 GetRevision() const { return Revision; }

	FOnBackpackStateChanged OnBackpackStateChanged;

	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

	UPROPERTY(BlueprintReadOnly)
	UInventoryModel* InventoryModel;

	UPROPERTY(BlueprintReadOnly)
	UMVVM_Backpack* InventoryVM;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Backpack")
	TObjectPtr<UBackpackItemDefinitions> ItemDefinitions;

private:
	friend class UEquipmentComponent;
	bool bEquipmentMutation = false;
	UFUNCTION()
	void OnRep_Inventory();

	bool HasServerAuthority() const;
	AMyPlayerController* GetOwningPlayerController() const;
	void InitializeReplicatedSlots();
	void ResizeReplicatedSlots(int32 NewCapacity);
	void SynchronizeReplicatedSlotsFromModel();

	UPROPERTY(ReplicatedUsing = OnRep_Inventory)
	FReplicatedInventoryList ReplicatedSlots;

	UPROPERTY(ReplicatedUsing = OnRep_Inventory)
	int32 Capacity = 16;

	UPROPERTY(ReplicatedUsing = OnRep_Inventory)
	int32 Revision = 0;
};
