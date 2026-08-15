// Fill out your copyright notice in the Description page of Project Settings.


#include "Backpack/BackpackComponent.h"
#include "Backpack/InventoryModel.h"
#include "UI/ViewModel/MVVM_InventorySlot.h"
#include "UI/ViewModel/MVVM_Backpack.h"

// Sets default values
void UBackpackComponent::BeginPlay()
{
    Super::BeginPlay();
    InventoryModel = NewObject<UInventoryModel>(this);
    InventoryVM = NewObject<UMVVM_Backpack>(this);
    InventoryVM->Initialize(InventoryModel);
}

void UBackpackComponent::PickupItem(const FInventoryItem& Item)
{
    if (InventoryModel) InventoryModel->AddItem(Item);
}