// Fill out your copyright notice in the Description page of Project Settings.


#include "Backpack/InventoryModel.h"

#include "Backpack/ItemDefinition.h"

void UInventoryModel::InitializeSlots(int32 SlotCount)
{
    Slots.SetNum(FMath::Max(0, SlotCount));
}

FInventoryAddResult UInventoryModel::TryAddItem(const UItemDefinition* Definition, int32 Quantity)
{
	FInventoryAddResult Result;
	Result.RemainingQuantity = FMath::Max(Quantity, 0);
	if (!IsValid(Definition) || Result.RemainingQuantity == 0)
	{
		return Result;
	}

	const FPrimaryAssetId ItemDefinitionId = Definition->GetPrimaryAssetId();
	const int32 StackLimit = Definition->bStackable ? FMath::Max(1, Definition->MaxStack) : 1;
	ItemDefinitions.FindOrAdd(ItemDefinitionId) = const_cast<UItemDefinition*>(Definition);
	for (FInventorySlot& Slot : Slots)
	{
		if (Slot.ItemDefinitionId != ItemDefinitionId || Slot.Quantity >= StackLimit)
		{
			continue;
		}

		const int32 Accepted = FMath::Min(StackLimit - Slot.Quantity, Result.RemainingQuantity);
		Slot.Quantity += Accepted;
		Result.AcceptedQuantity += Accepted;
		Result.RemainingQuantity -= Accepted;
		if (Result.RemainingQuantity == 0)
		{
			Result.bSucceeded = true;
			OnInventoryUpdated.Broadcast(Slots);
			return Result;
		}
	}

	for (FInventorySlot& Slot : Slots)
	{
		if (!Slot.IsEmpty())
		{
			continue;
		}

		const int32 Accepted = FMath::Min(StackLimit, Result.RemainingQuantity);
		Slot.ItemDefinitionId = ItemDefinitionId;
		Slot.Quantity = Accepted;
		Result.AcceptedQuantity += Accepted;
		Result.RemainingQuantity -= Accepted;
		if (Result.RemainingQuantity == 0)
		{
			break;
		}
	}

	Result.bSucceeded = Result.AcceptedQuantity > 0;
	if (Result.bSucceeded)
	{
		OnInventoryUpdated.Broadcast(Slots);
	}
	return Result;
}

FInventoryAddResult UInventoryModel::TryAddItem(const FPrimaryAssetId& ItemDefinitionId, int32 Quantity)
{
	FInventoryAddResult Result;
	Result.RemainingQuantity = FMath::Max(Quantity, 0);
	const FBackpackItemDefEntry* Definition = FindItemDefinition(ItemDefinitionId);
	if (!Definition || Result.RemainingQuantity == 0)
	{
		return Result;
	}

	const int32 StackLimit = Definition->bStackable ? FMath::Max(1, Definition->MaxStack) : 1;
	for (FInventorySlot& Slot : Slots)
	{
		if (Slot.ItemDefinitionId != ItemDefinitionId || Slot.Quantity >= StackLimit)
		{
			continue;
		}

		const int32 Accepted = FMath::Min(StackLimit - Slot.Quantity, Result.RemainingQuantity);
		Slot.Quantity += Accepted;
		Result.AcceptedQuantity += Accepted;
		Result.RemainingQuantity -= Accepted;
		if (Result.RemainingQuantity == 0)
		{
			Result.bSucceeded = true;
			OnInventoryUpdated.Broadcast(Slots);
			return Result;
		}
	}

	for (FInventorySlot& Slot : Slots)
	{
		if (!Slot.IsEmpty())
		{
			continue;
		}

		const int32 Accepted = FMath::Min(StackLimit, Result.RemainingQuantity);
		Slot.ItemDefinitionId = ItemDefinitionId;
		Slot.Quantity = Accepted;
		Result.AcceptedQuantity += Accepted;
		Result.RemainingQuantity -= Accepted;
		if (Result.RemainingQuantity == 0)
		{
			break;
		}
	}

	Result.bSucceeded = Result.AcceptedQuantity > 0;
	if (Result.bSucceeded)
	{
		OnInventoryUpdated.Broadcast(Slots);
	}
	return Result;
}

void UInventoryModel::SetItemDefinitions(UBackpackItemDefinitions* InItemDefinitions)
{
	ItemDefinitionCatalog = InItemDefinitions;
}

const FBackpackItemDefEntry* UInventoryModel::FindItemDefinition(const FPrimaryAssetId& ItemDefinitionId) const
{
	return IsValid(ItemDefinitionCatalog) ? ItemDefinitionCatalog->FindDefinition(ItemDefinitionId) : nullptr;
}

bool UInventoryModel::UseItemAt(int32 SlotIndex)
{
	if (!Slots.IsValidIndex(SlotIndex) || Slots[SlotIndex].IsEmpty())
	{
		return false;
	}

	const FBackpackItemDefEntry* CatalogDefinition = FindItemDefinition(Slots[SlotIndex].ItemDefinitionId);
	UItemDefinition* LegacyDefinition = ItemDefinitions.FindRef(Slots[SlotIndex].ItemDefinitionId);
	if ((CatalogDefinition && !CatalogDefinition->bUsable) || (!CatalogDefinition && (!IsValid(LegacyDefinition) || !LegacyDefinition->bUsable)))
	{
		return false;
	}

	FInventorySlot& Slot = Slots[SlotIndex];
	--Slot.Quantity;
	if (Slot.Quantity <= 0)
	{
		Slot.Clear();
	}
	OnInventoryUpdated.Broadcast(Slots);
	return true;
}

void UInventoryModel::DeleteItem(FName ItemID, int32 Count)
{
    int32 Idx = Items.IndexOfByPredicate([&](const FInventoryItem& I) { return I.ItemID == ItemID; });
    if (Idx == INDEX_NONE) return;

    Items[Idx].Quantity -= Count;
    if (Items[Idx].Quantity <= 0) Items.RemoveAt(Idx);
    OnInventoryUpdated.Broadcast(Slots); // 只广播库存更新，不触发掉落逻辑
}
void UInventoryModel::UseItem(FName ItemID)
{
    int32 Idx = Items.IndexOfByPredicate([&](const FInventoryItem& I) { return I.ItemID == ItemID; });
    if (Idx == INDEX_NONE) return;

    Items[Idx].Quantity -= 1;
    if (Items[Idx].Quantity <= 0) Items.RemoveAt(Idx);
    //use logic


    //
    OnInventoryUpdated.Broadcast(Slots); // 只广播库存更新，不触发掉落逻辑
}

void UInventoryModel::AddItem(const FInventoryItem& NewItem)
{
    for (auto& It : Items)
    {
        if (It.ItemID == NewItem.ItemID && It.Quantity < It.MaxStack)
        {
            It.Quantity = FMath::Min(It.Quantity + NewItem.Quantity, It.MaxStack);
            OnInventoryUpdated.Broadcast(Slots);
            return;
        }
    }
    if (Items.Num() < MaxSlots)
    {
        Items.Add(NewItem);
        OnInventoryUpdated.Broadcast(Slots);
    }
}

void UInventoryModel::RemoveItem(FName ItemID, int32 Count)
{
    int32 Idx = Items.IndexOfByPredicate([&](const FInventoryItem& I) { return I.ItemID == ItemID; });
    if (Idx == INDEX_NONE) return;
    Items[Idx].Quantity -= Count;
    if (Items[Idx].Quantity <= 0) Items.RemoveAt(Idx);
    OnInventoryUpdated.Broadcast(Slots);
}

bool UInventoryModel::SwapSlots(int32 IndexA, int32 IndexB)
{
	if (!Slots.IsValidIndex(IndexA) || !Slots.IsValidIndex(IndexB) || IndexA == IndexB)
	{
		return false;
	}

	Swap(Slots[IndexA], Slots[IndexB]);
	OnInventoryUpdated.Broadcast(Slots);
	return true;
}

void UInventoryModel::ApplyReplicatedSlots(const TArray<FReplicatedInventorySlot>& ReplicatedSlots, int32 NewMaxSlots)
{
	const int32 ClampedMaxSlots = FMath::Max(0, NewMaxSlots);
	const bool bMaxSlotsChanged = MaxSlots != ClampedMaxSlots;
	MaxSlots = ClampedMaxSlots;
	Slots.SetNum(MaxSlots);

	for (int32 SlotIndex = 0; SlotIndex < Slots.Num(); ++SlotIndex)
	{
		FInventorySlot& LocalSlot = Slots[SlotIndex];
		if (ReplicatedSlots.IsValidIndex(SlotIndex) && !ReplicatedSlots[SlotIndex].IsEmpty())
		{
			LocalSlot.ItemDefinitionId = ReplicatedSlots[SlotIndex].ItemDefinitionId;
			LocalSlot.Quantity = ReplicatedSlots[SlotIndex].Quantity;
		}
		else
		{
			LocalSlot.Clear();
		}
	}

	if (bMaxSlotsChanged)
	{
		OnInventoryMaxSlotsChanged.Broadcast(MaxSlots);
	}
	OnInventoryUpdated.Broadcast(Slots);
}

void UInventoryModel::SetMaxSlots(int32 NewMaxSlots)
{
    const int32 ClampedMaxSlots = FMath::Max(0, NewMaxSlots);
    if (ClampedMaxSlots == MaxSlots && Slots.Num() == ClampedMaxSlots)
    {
        return;
    }

    TArray<FInventorySlot> DiscardedSlots;
    if (Slots.Num() > ClampedMaxSlots)
    {
        for (int32 Index = ClampedMaxSlots; Index < Slots.Num(); ++Index)
        {
            if (!Slots[Index].IsEmpty())
            {
                DiscardedSlots.Add(Slots[Index]);
            }
        }
    }

    MaxSlots = ClampedMaxSlots;
    Slots.SetNum(MaxSlots);
    if (!DiscardedSlots.IsEmpty())
    {
        OnSlotsDiscarded.Broadcast(DiscardedSlots);
    }
    OnInventoryMaxSlotsChanged.Broadcast(MaxSlots);
    OnInventoryUpdated.Broadcast(Slots);
}
