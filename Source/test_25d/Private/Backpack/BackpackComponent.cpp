// Fill out your copyright notice in the Description page of Project Settings.


#include "Backpack/BackpackComponent.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ItemDefinition.h"
#include "UI/ViewModel/MVVM_InventorySlot.h"
#include "UI/ViewModel/MVVM_Backpack.h"
#include "Net/UnrealNetwork.h"

UBackpackComponent::UBackpackComponent()
{
	SetIsReplicatedByDefault(true);
}

void UBackpackComponent::Initialize()
{
    if (IsValid(InventoryModel))
    {
        return;
    }
    InventoryModel = NewObject<UInventoryModel>(this);
    if (HasServerAuthority())
    {
        InitializeReplicatedSlots();
        InventoryModel->ApplyReplicatedSlots(ReplicatedSlots.Items, Capacity);
    }
    else
    {
        InventoryModel->ApplyReplicatedSlots(ReplicatedSlots.Items, Capacity);
    }
    InventoryVM = NewObject<UMVVM_Backpack>(this);
    InventoryVM->Initialize(InventoryModel);
}

FInventoryAddResult UBackpackComponent::TryAddItem(const UItemDefinition* Definition, int32 Quantity)
{
	FInventoryAddResult Result;
	if (!HasServerAuthority() || !IsValid(Definition) || Quantity <= 0)
	{
		return Result;
	}

	Initialize();
	Result = InventoryModel->TryAddItem(Definition, Quantity);
	if (Result.bSucceeded)
	{
		SynchronizeReplicatedSlotsFromModel();
	}
	return Result;
}

bool UBackpackComponent::SwapSlots(int32 IndexA, int32 IndexB)
{
	if (!HasServerAuthority())
	{
		return false;
	}

	Initialize();
	if (!InventoryModel->SwapSlots(IndexA, IndexB))
	{
		return false;
	}

	SynchronizeReplicatedSlotsFromModel();
	return true;
}

bool UBackpackComponent::UseItemAt(int32 SlotIndex)
{
	if (!HasServerAuthority())
	{
		return false;
	}

	Initialize();
	if (!InventoryModel->UseItemAt(SlotIndex))
	{
		return false;
	}

	SynchronizeReplicatedSlotsFromModel();
	return true;
}

void UBackpackComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);
	DOREPLIFETIME(UBackpackComponent, ReplicatedSlots);
	DOREPLIFETIME(UBackpackComponent, Capacity);
	DOREPLIFETIME(UBackpackComponent, Revision);
}

void UBackpackComponent::OnRep_Inventory()
{
	Initialize();
	InventoryModel->ApplyReplicatedSlots(ReplicatedSlots.Items, Capacity);
}

bool UBackpackComponent::HasServerAuthority() const
{
	return GetOwner() && GetOwner()->HasAuthority();
}

void UBackpackComponent::InitializeReplicatedSlots()
{
	if (ReplicatedSlots.Items.Num() >= Capacity)
	{
		return;
	}

	const int32 FirstNewSlot = ReplicatedSlots.Items.Num();
	ReplicatedSlots.Items.SetNum(Capacity);
	for (int32 SlotIndex = FirstNewSlot; SlotIndex < ReplicatedSlots.Items.Num(); ++SlotIndex)
	{
		ReplicatedSlots.MarkItemDirty(ReplicatedSlots.Items[SlotIndex]);
	}
}

void UBackpackComponent::SynchronizeReplicatedSlotsFromModel()
{
	check(HasServerAuthority());
	const TArray<FInventorySlot>& ModelSlots = InventoryModel->GetSlots();
	check(ModelSlots.Num() == ReplicatedSlots.Items.Num());

	bool bChanged = false;
	for (int32 SlotIndex = 0; SlotIndex < ModelSlots.Num(); ++SlotIndex)
	{
		FReplicatedInventorySlot& ReplicatedSlot = ReplicatedSlots.Items[SlotIndex];
		const FInventorySlot& ModelSlot = ModelSlots[SlotIndex];
		if (ReplicatedSlot.ItemDefinitionId == ModelSlot.ItemDefinitionId && ReplicatedSlot.Quantity == ModelSlot.Quantity)
		{
			continue;
		}

		ReplicatedSlot.ItemDefinitionId = ModelSlot.ItemDefinitionId;
		ReplicatedSlot.Quantity = ModelSlot.Quantity;
		ReplicatedSlots.MarkItemDirty(ReplicatedSlot);
		bChanged = true;
	}

	if (bChanged)
	{
		++Revision;
	}
}
