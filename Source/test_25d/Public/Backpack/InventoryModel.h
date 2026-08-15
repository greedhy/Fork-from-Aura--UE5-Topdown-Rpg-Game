// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "InventoryModel.generated.h"

/**
 * 
 */

USTRUCT(BlueprintType)
struct FInventoryItem
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FName ItemID;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FText DisplayName;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    TSoftObjectPtr<UTexture2D> Icon;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    int32 Quantity = 1;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    int32 MaxStack = 99;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    bool bIsUsable = false;
};

USTRUCT(BlueprintType)
struct FInventorySlot
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly)
    FName ItemID = NAME_None;

    UPROPERTY(BlueprintReadOnly)
    int32 Quantity = 0;

    bool IsEmpty() const
    {
        return ItemID.IsNone() || Quantity <= 0;
    }

    void Clear()
    {
        ItemID = NAME_None;
        Quantity = 0;
    }
};

DECLARE_MULTICAST_DELEGATE_OneParam(FOnInventoryUpdated, const TArray<FInventoryItem>&);
DECLARE_MULTICAST_DELEGATE_OneParam(FOnInventoryMaxSlotsChanged, int32 /*NewMaxSlots*/);

UCLASS()
class TEST_25D_API UInventoryModel : public UObject
{
    GENERATED_BODY()
public:
    void InitializeSlots(int32 SlotCount);

    const TArray<FInventorySlot>& GetSlots() const { return Slots; }

    // InventoryModel.h 新增
    UFUNCTION(BlueprintCallable, Category = "Inventory")
    void DeleteItem(FName ItemID, int32 Count);
    UFUNCTION(BlueprintCallable, Category = "Inventory")
    void UseItem(FName ItemID); // 直接删除，不触发掉落
    UFUNCTION(BlueprintCallable)
    void AddItem(const FInventoryItem& NewItem);

    UFUNCTION(BlueprintCallable)
    void RemoveItem(FName ItemID, int32 Count);

    UFUNCTION(BlueprintCallable)
    void SwapSlots(int32 IndexA, int32 IndexB);

    const TArray<FInventoryItem>& GetItems() const { return Items; }

    FOnInventoryUpdated OnInventoryUpdated;

    // 动态格数接口
    UFUNCTION(BlueprintCallable, Category = "Inventory")
    void SetMaxSlots(int32 NewMaxSlots);

    UFUNCTION(BlueprintPure, Category = "Inventory")
    int32 GetMaxSlots() const { return MaxSlots; }

    FOnInventoryMaxSlotsChanged OnInventoryMaxSlotsChanged;  // 格数变化广播

private:
    UPROPERTY()
    TArray<FInventorySlot> Slots;

    UPROPERTY()
    TArray<FInventoryItem> Items;

    int32 MaxSlots = 16;
	
};


