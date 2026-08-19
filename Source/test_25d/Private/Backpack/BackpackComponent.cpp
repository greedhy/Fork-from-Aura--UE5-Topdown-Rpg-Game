// Fill out your copyright notice in the Description page of Project Settings.


#include "Backpack/BackpackComponent.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ItemDefinition.h"
#include "UI/ViewModel/MVVM_InventorySlot.h"
#include "UI/ViewModel/MVVM_Backpack.h"
#include "Net/UnrealNetwork.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "GameplayEffect.h"
#include "GameFramework/Pawn.h"

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
    }
    InventoryModel->ApplyReplicatedSlots(ReplicatedSlots.Items, Capacity);
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

bool UBackpackComponent::TryUseItemForPawn(int32 SlotIndex, APawn* Pawn)
{
	if (!HasServerAuthority() || !IsValid(Pawn))
	{
		return false;
	}

	Initialize();
	const TArray<FInventorySlot>& Slots = InventoryModel->GetSlots();
	if (!Slots.IsValidIndex(SlotIndex) || Slots[SlotIndex].IsEmpty())
	{
		return false;
	}

	UItemDefinition* Definition = InventoryModel->ItemDefinitions.FindRef(Slots[SlotIndex].ItemDefinitionId);
	if (!IsValid(Definition) || !Definition->bUsable || !Definition->UseEffect)
	{
		return false;
	}

	UAbilitySystemComponent* TargetAbilitySystem = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Pawn);
	if (!IsValid(TargetAbilitySystem))
	{
		return false;
	}

	FGameplayEffectContextHandle EffectContext = TargetAbilitySystem->MakeEffectContext();
	EffectContext.AddSourceObject(Definition);
	const FGameplayEffectSpecHandle EffectSpec = TargetAbilitySystem->MakeOutgoingSpec(Definition->UseEffect, 1.f, EffectContext);
	if (!EffectSpec.IsValid())
	{
		return false;
	}

	const FActiveGameplayEffectHandle AppliedEffect = TargetAbilitySystem->ApplyGameplayEffectSpecToSelf(*EffectSpec.Data.Get());
	if (!AppliedEffect.IsValid() || !InventoryModel->UseItemAt(SlotIndex))
	{
		return false;
	}

	SynchronizeReplicatedSlotsFromModel();
	return true;
}

bool UBackpackComponent::SetCapacity(int32 NewCapacity)
{
	if (!HasServerAuthority())
	{
		return false;
	}

	const int32 ClampedCapacity = FMath::Max(0, NewCapacity);
	if (Capacity == ClampedCapacity)
	{
		return false;
	}

	Initialize();
	InventoryModel->SetMaxSlots(ClampedCapacity);
	ResizeReplicatedSlots(ClampedCapacity);
	Capacity = ClampedCapacity;
	++Revision;
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
	ResizeReplicatedSlots(Capacity);
}

void UBackpackComponent::ResizeReplicatedSlots(int32 NewCapacity)
{
	if (NewCapacity < ReplicatedSlots.Items.Num())
	{
		ReplicatedSlots.Items.SetNum(NewCapacity);
		ReplicatedSlots.MarkArrayDirty();
		return;
	}

	const int32 FirstNewSlot = ReplicatedSlots.Items.Num();
	ReplicatedSlots.Items.SetNum(NewCapacity);
	for (int32 SlotIndex = FirstNewSlot; SlotIndex < NewCapacity; ++SlotIndex)
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
