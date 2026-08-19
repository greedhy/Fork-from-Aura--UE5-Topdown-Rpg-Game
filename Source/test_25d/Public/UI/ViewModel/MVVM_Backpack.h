// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "MVVMViewModelBase.h"
#include "Backpack/InventoryModel.h"
#include "MVVM_Backpack.generated.h"

class UMVVM_InventorySlot;
class UInventoryModel;
class AMyPlayerController;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FSetItemIndex, int32, WidgetSwitcherIndex);
DECLARE_MULTICAST_DELEGATE_OneParam(FOnInventoryDropRequested, int32 /*SlotIndex*/);
DECLARE_MULTICAST_DELEGATE_TwoParams(FOnInventorySwapRequested, int32 /*SourceSlotIndex*/, int32 /*TargetSlotIndex*/);
DECLARE_MULTICAST_DELEGATE_OneParam(FOnInventoryUseRequested, int32 /*SlotIndex*/);
DECLARE_MULTICAST_DELEGATE_TwoParams(FOnInventoryDeleteRequested, int32 /*SlotIndex*/, int32 /*Count*/);


UCLASS(Blueprintable, DisplayName = "Backpack ViewModel")
class TEST_25D_API UMVVM_Backpack : public UMVVMViewModelBase
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable)
    void Initialize(UInventoryModel* InModel, AMyPlayerController* InOwningPlayerController = nullptr);
    void SetOwningPlayerController(AMyPlayerController* InOwningPlayerController);

    // 供 TileView/ListView 绑定——必须返回 TArray<UObject*>，并手动广播
    UFUNCTION(BlueprintPure, FieldNotify)
    TArray<UObject*> GetSlotViewModels() const { return SlotVMs; }

    UFUNCTION(BlueprintCallable)
    void RequestDrop(int32 SlotIndex);

    UFUNCTION(BlueprintCallable)
    void RequestSwap(int32 From, int32 To);

    UFUNCTION(BlueprintPure)
    int32 GetSlotCount() const { return SlotVMs.Num(); }

    // 动态格数：返回当前最大格数
    UFUNCTION(BlueprintPure, FieldNotify)
    int32 GetMaxSlots() const { return MaxSlotsCache; }

    // === 拖拽接口（UI调用）===
    UFUNCTION(BlueprintCallable, Category = "Inventory|Drag")
    bool RequestBeginDrag(int32 SourceSlotIndex);  // 开始拖拽

    UFUNCTION(BlueprintCallable, Category = "Inventory|Drag")
    bool RequestDropOnSlot(int32 TargetSlotIndex); // 放置到目标槽位

    UFUNCTION(BlueprintCallable, Category = "Inventory|Drag")
    void RequestCancelDrag();                      // 取消拖拽（拖出背包）

    UFUNCTION(BlueprintCallable, Category = "Inventory|Drag")
    void RequestHoverSlot(int32 HoverSlotIndex);   // 拖拽悬停到某槽位

    UFUNCTION(BlueprintPure, FieldNotify)
    bool IsDragging() const { return bIsDragging; } // 是否正在拖拽

  
    UFUNCTION(BlueprintPure, FieldNotify)
    FText GetMaxSlotsText() const {
        return FText::Format(
            FText::FromString("容量：{0}"),
            FText::AsNumber(MaxSlotsCache)
        );
    };


    // 选中相关
    UFUNCTION(BlueprintCallable, Category = "Inventory|Selection")
    void SelectSlot(int32 SlotIndex); // 选中指定槽位

    UFUNCTION(BlueprintPure, FieldNotify)
    int32 GetCurrentSelectedIndex() const { return CurrentSelectedIndex; }

    UFUNCTION(BlueprintPure, FieldNotify)
    bool HasSelectedItem() const { return IsValid(Model) && Model->GetSlots().IsValidIndex(CurrentSelectedIndex) && !Model->GetSlots()[CurrentSelectedIndex].IsEmpty(); }

    // 操作接口（对应使用/删除按钮）
    UFUNCTION(BlueprintCallable, Category = "Inventory|Action")
    bool RequestUseSelectedItem(); // 使用选中物品

    UFUNCTION(BlueprintCallable, Category = "Inventory|Action")
    bool RequestDeleteSelectedItem(int32 Count = 1); // 删除选中物品，默认删1个

    // 选中物品详情（UI绑定显示）
    UFUNCTION(BlueprintPure, FieldNotify)
    FText GetSelectedItemName() const;

    // 当前选中索引（-1=未选中）
    UPROPERTY(BlueprintReadOnly, FieldNotify, meta = (AllowPrivateAccess = true))
    int32 CurrentSelectedIndex = INDEX_NONE;

    // 重置选中状态（数据变化时调用）
    void ResetSelection();

	FOnInventoryDropRequested OnDropRequested;
	FOnInventorySwapRequested OnSwapRequested;
	FOnInventoryUseRequested OnUseRequested;
	FOnInventoryDeleteRequested OnDeleteRequested;
private:
    UPROPERTY()
    UInventoryModel* Model = nullptr;

    TWeakObjectPtr<AMyPlayerController> OwningPlayerController;

    UPROPERTY(BlueprintReadOnly, FieldNotify, meta = (AllowPrivateAccess = true))
    TArray<UObject*> SlotVMs;

    UPROPERTY()
    TArray<TObjectPtr<UMVVM_InventorySlot>> SlotVMsTyped;

    UFUNCTION()
    void RebuildFromModel();

    UPROPERTY(EditDefaultsOnly)
    TSubclassOf<UMVVM_Backpack> UMVVM_BackpackClass;

    UFUNCTION()
    void HandleInventoryUpdated(const TArray<FInventorySlot>& Slots);

    // 槽位VM池（避免反复NewObject，性能优化）
    UPROPERTY()
    TArray<TObjectPtr<UMVVM_InventorySlot>> SlotVMPool;

    int32 MaxSlotsCache = 0;

    // 拖拽临时状态（未提交到Model，避免拖拽过程中频繁修改数据）
    bool bIsDragging = false;
    int32 DragSourceIndex = INDEX_NONE;
    int32 CurrentHoverIndex = INDEX_NONE;

    UFUNCTION()
    void OnMaxSlotsChanged(int32 NewMaxSlots);

    void ClearDragState();  // 清理拖拽临时状态

};


