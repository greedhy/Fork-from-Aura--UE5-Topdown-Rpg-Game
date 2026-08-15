// Fill out your copyright notice in the Description page of Project Settings.


#include "Backpack/InventoryModel.h"

void UInventoryModel::InitializeSlots(int32 SlotCount)
{
    Slots.SetNum(FMath::Max(0, SlotCount));
}

void UInventoryModel::DeleteItem(FName ItemID, int32 Count)
{
    int32 Idx = Items.IndexOfByPredicate([&](const FInventoryItem& I) { return I.ItemID == ItemID; });
    if (Idx == INDEX_NONE) return;

    Items[Idx].Quantity -= Count;
    if (Items[Idx].Quantity <= 0) Items.RemoveAt(Idx);
    OnInventoryUpdated.Broadcast(Items); // 只广播库存更新，不触发掉落逻辑
}
void UInventoryModel::UseItem(FName ItemID)
{
    int32 Idx = Items.IndexOfByPredicate([&](const FInventoryItem& I) { return I.ItemID == ItemID; });
    if (Idx == INDEX_NONE) return;

    Items[Idx].Quantity -= 1;
    if (Items[Idx].Quantity <= 0) Items.RemoveAt(Idx);
    //use logic


    //
    OnInventoryUpdated.Broadcast(Items); // 只广播库存更新，不触发掉落逻辑
}

void UInventoryModel::AddItem(const FInventoryItem& NewItem)
{
    for (auto& It : Items)
    {
        if (It.ItemID == NewItem.ItemID && It.Quantity < It.MaxStack)
        {
            It.Quantity = FMath::Min(It.Quantity + NewItem.Quantity, It.MaxStack);
            OnInventoryUpdated.Broadcast(Items);
            return;
        }
    }
    if (Items.Num() < MaxSlots)
    {
        Items.Add(NewItem);
        OnInventoryUpdated.Broadcast(Items);
    }
}

void UInventoryModel::RemoveItem(FName ItemID, int32 Count)
{
    int32 Idx = Items.IndexOfByPredicate([&](const FInventoryItem& I) { return I.ItemID == ItemID; });
    if (Idx == INDEX_NONE) return;
    Items[Idx].Quantity -= Count;
    if (Items[Idx].Quantity <= 0) Items.RemoveAt(Idx);
    OnInventoryUpdated.Broadcast(Items);
}

void UInventoryModel::SwapSlots(int32 IndexA, int32 IndexB)
{
    if (Items.IsValidIndex(IndexA) && Items.IsValidIndex(IndexB))
    {
        Swap(Items[IndexA], Items[IndexB]);
        OnInventoryUpdated.Broadcast(Items);
    }
}

void UInventoryModel::SetMaxSlots(int32 NewMaxSlots)
{
    if (NewMaxSlots == MaxSlots || NewMaxSlots <= 0) return;

    MaxSlots = NewMaxSlots;
    // 如果新格数比现有物品少，截断多余物品（可按需求改成不删除，只限制新增）
    if (Items.Num() > MaxSlots)
    {
        Items.SetNum(MaxSlots);
    }
    OnInventoryMaxSlotsChanged.Broadcast(MaxSlots);
    OnInventoryUpdated.Broadcast(Items);  // 触发ViewModel重建
}
