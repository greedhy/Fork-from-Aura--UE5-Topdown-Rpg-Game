// Fill out your copyright notice in the Description page of Project Settings.


#include "UI/ViewModel/MVVM_Backpack.h"

#include "MVVMViewModelBase.h"
#include "Backpack/InventoryModel.h"
#include "UI/ViewModel/MVVM_InventorySlot.h"



void UMVVM_Backpack::Initialize(UInventoryModel* InModel)
{
    Model = InModel;
    if (Model)
    {
        Model->OnInventoryUpdated.AddUObject(this, &UMVVM_Backpack::HandleInventoryUpdated);
    }
    SlotVMsTyped.SetNum(16);
    for (int32 i = 0; i < 16; ++i)
    {
        SlotVMsTyped[i] = NewObject<UMVVM_InventorySlot>(this);
    }
}
void UMVVM_Backpack::HandleInventoryUpdated(const TArray<FInventoryItem>& Items)
{
    RebuildFromModel();

}

void UMVVM_Backpack::RebuildFromModel()
{
    if (!Model) return;
    const TArray<FInventoryItem>& Items = Model->GetItems();
    SlotVMs.Reset();
    if (CurrentSelectedIndex >= Items.Num() || CurrentSelectedIndex < 0)
    {
        ResetSelection();
    }
    for (int32 i = 0; i < 16; ++i)
    {
        UMVVM_InventorySlot* VM = SlotVMsTyped[i];
        if (i < Items.Num())
        {
            VM->SetEmpty(false);
            VM->SetIcon(Items[i].Icon);
            VM->SetStackCount(Items[i].Quantity);
        }
        else
        {
            VM->SetEmpty(true);
            VM->SetIcon(nullptr);
            VM->SetStackCount(0);
        }
        SlotVMs.Add(VM);
    }
    UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(GetSlotViewModels);

  
}

void UMVVM_Backpack::RequestDrop(int32 SlotIndex)
{
    if (!Model) return;
    const TArray<FInventoryItem>& Items = Model->GetItems();
    if (Items.IsValidIndex(SlotIndex))
    {
        Model->RemoveItem(Items[SlotIndex].ItemID, Items[SlotIndex].Quantity);
    }
}

void UMVVM_Backpack::RequestSwap(int32 From, int32 To)
{
    if (Model) Model->SwapSlots(From, To);
}

// ==================== 拖拽逻辑 ====================
bool UMVVM_Backpack::RequestBeginDrag(int32 SourceSlotIndex)
{
    if (!IsValid(Model) || !Model->GetItems().IsValidIndex(SourceSlotIndex))
        return false;

    const TArray<FInventoryItem>& Items = Model->GetItems();
    DraggedItemCache = Items[SourceSlotIndex];
    DragSourceIndex = SourceSlotIndex;
    bIsDragging = true;

    // 标记源槽位为拖拽状态，UI自动更新样式
    if (SlotVMPool.IsValidIndex(SourceSlotIndex))
    {
        SlotVMPool[SourceSlotIndex]->SetDragSource(true);
    }

    UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(IsDragging);
    return true;
}

bool UMVVM_Backpack::RequestDropOnSlot(int32 TargetSlotIndex)
{
    if (!bIsDragging || !IsValid(Model) || DragSourceIndex == INDEX_NONE)
    {
        ClearDragState();
        return false;
    }

    const TArray<FInventoryItem>& Items = Model->GetItems();
    bool bSuccess = false;

    // 目标槽位有效
    if (Items.IsValidIndex(TargetSlotIndex))
    {
        const FInventoryItem& TargetItem = Items[TargetSlotIndex];
        // 1. 同ID可堆叠：合并数量
        if (TargetItem.ItemID == DraggedItemCache.ItemID && DraggedItemCache.bIsUsable)
        {
            const int32 Total = TargetItem.Quantity + DraggedItemCache.Quantity;
            if (Total <= TargetItem.MaxStack)
            {
                Model->RemoveItem(DraggedItemCache.ItemID, DraggedItemCache.Quantity);
                bSuccess = true;
            }
            else
            {
                // 超出堆叠上限：拆分后交换
                const int32 Remaining = Total - TargetItem.MaxStack;
                Model->RemoveItem(DraggedItemCache.ItemID, DraggedItemCache.Quantity - Remaining);
                Model->SwapSlots(DragSourceIndex, TargetSlotIndex);
                bSuccess = true;
            }
        }
        // 2. 不同物品/不可堆叠：直接交换
        else
        {
            Model->SwapSlots(DragSourceIndex, TargetSlotIndex);
            bSuccess = true;
        }
    }
    // 目标槽位为空且在有效范围内
    else if (TargetSlotIndex < Model->GetMaxSlots())
    {
        Model->AddItem(DraggedItemCache);
        Model->RemoveItem(DraggedItemCache.ItemID, DraggedItemCache.Quantity);
        bSuccess = true;
    }

    ClearDragState();
    return bSuccess;
}

void UMVVM_Backpack::RequestCancelDrag()
{
    ClearDragState();
}

void UMVVM_Backpack::RequestHoverSlot(int32 HoverSlotIndex)
{
    if (!bIsDragging || CurrentHoverIndex == HoverSlotIndex)
        return;

    // 清除上一个悬停槽位的状态
    if (SlotVMPool.IsValidIndex(CurrentHoverIndex))
    {
        SlotVMPool[CurrentHoverIndex]->SetDragHovered(false);
    }
    // 设置新的悬停槽位状态
    if (SlotVMPool.IsValidIndex(HoverSlotIndex))
    {
        SlotVMPool[HoverSlotIndex]->SetDragHovered(true);
    }
    CurrentHoverIndex = HoverSlotIndex;
}

void UMVVM_Backpack::ClearDragState()
{
    // 重置所有槽位的拖拽状态
    if (SlotVMPool.IsValidIndex(DragSourceIndex))
    {
        SlotVMPool[DragSourceIndex]->SetDragSource(false);
    }
    if (SlotVMPool.IsValidIndex(CurrentHoverIndex))
    {
        SlotVMPool[CurrentHoverIndex]->SetDragHovered(false);
    }

    bIsDragging = false;
    DragSourceIndex = INDEX_NONE;
    CurrentHoverIndex = INDEX_NONE;
    DraggedItemCache = FInventoryItem();

    UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(IsDragging);
}
void UMVVM_Backpack::OnMaxSlotsChanged(int32 NewMaxSlots)
{
    if (MaxSlotsCache != NewMaxSlots)
    {
        MaxSlotsCache = NewMaxSlots;
        UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(GetMaxSlots);
        RebuildFromModel();  // 格数变化，重建SlotVM数组
    }
}

void UMVVM_Backpack::SelectSlot(int32 SlotIndex)
{
    if (!IsValid(Model)) return;
    const TArray<FInventoryItem>& Items = Model->GetItems();

    // 1. 取消之前选中的槽位
    if (CurrentSelectedIndex != INDEX_NONE && SlotVMsTyped.IsValidIndex(CurrentSelectedIndex))
    {
        SlotVMsTyped[CurrentSelectedIndex]->SetSelected(false);
        SlotVMsTyped[CurrentSelectedIndex]->SetCanBeUsed(false);
    }

    // 2. 选中新槽位（点击空白/无效索引则取消选中）
    if (Items.IsValidIndex(SlotIndex))
    {
        CurrentSelectedIndex = SlotIndex;
        SlotVMsTyped[SlotIndex]->SetSelected(true);
        SlotVMsTyped[SlotIndex]->SetCanBeUsed(Items[SlotIndex].bIsUsable);
    }
    else
    {
        CurrentSelectedIndex = INDEX_NONE;
    }

    UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(GetCurrentSelectedIndex);
    UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(HasSelectedItem);
    UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(GetSelectedItemName);
}

bool UMVVM_Backpack::RequestUseSelectedItem()
{
    if (!HasSelectedItem()) return false;
    //
    return true;
  //  return UInventoryModel::UseItem(GetSelectedItemName());
}

bool UMVVM_Backpack::RequestDeleteSelectedItem(int32 Count)
{
    if (!HasSelectedItem()) return false;
    const TArray<FInventoryItem>& Items = Model->GetItems();
    const FInventoryItem& SelectedItem = Items[CurrentSelectedIndex];

    Model->DeleteItem(SelectedItem.ItemID, Count);
    ResetSelection(); // 删除后取消选中
    return true;
}

FText UMVVM_Backpack::GetSelectedItemName() const
{
    if (!HasSelectedItem()) return FText::GetEmpty();
    const TArray<FInventoryItem>& Items = Model->GetItems();
    return Items[CurrentSelectedIndex].DisplayName;
}

void UMVVM_Backpack::ResetSelection()
{
    if (CurrentSelectedIndex != INDEX_NONE && SlotVMsTyped.IsValidIndex(CurrentSelectedIndex))
    {
        SlotVMsTyped[CurrentSelectedIndex]->SetSelected(false);
        SlotVMsTyped[CurrentSelectedIndex]->SetCanBeUsed(false);
    }
    CurrentSelectedIndex = INDEX_NONE;
    UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(HasSelectedItem);
}