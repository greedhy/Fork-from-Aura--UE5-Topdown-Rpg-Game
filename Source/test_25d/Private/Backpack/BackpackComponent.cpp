// Fill out your copyright notice in the Description page of Project Settings.


#include "Backpack/BackpackComponent.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ItemDefinition.h"
#include "Backpack/WorldPickup.h"
#include "Player/MyPlayerController.h"
#include "Player/MyPlayerState.h"
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
		if (IsValid(InventoryVM))
		{
			InventoryVM->SetOwningPlayerController(GetOwningPlayerController());
		}
        return;
    }
    InventoryModel = NewObject<UInventoryModel>(this);
    if (HasServerAuthority())
    {
        InitializeReplicatedSlots();
    }
    InventoryModel->ApplyReplicatedSlots(ReplicatedSlots.Items, Capacity);
    InventoryVM = NewObject<UMVVM_Backpack>(this);
    InventoryVM->Initialize(InventoryModel, GetOwningPlayerController());
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
		OnBackpackStateChanged.Broadcast();
	}
	return Result;
}

FInventoryAddResult UBackpackComponent::TryPickup(AWorldPickup* Pickup)
{
	FInventoryAddResult Result;
	if (!HasServerAuthority() || !IsValid(Pickup) || !Pickup->HasAuthority() || !IsValid(Pickup->GetItemDefinition()) || Pickup->GetQuantity() <= 0)
	{
		return Result;
	}

	Result = TryAddItem(Pickup->GetItemDefinition(), Pickup->GetQuantity());
	if (Result.AcceptedQuantity > 0 && !Pickup->ConsumeQuantity(Result.AcceptedQuantity))
	{
		return FInventoryAddResult();
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
	OnBackpackStateChanged.Broadcast();
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
	if (!AppliedEffect.WasSuccessfullyApplied() || !InventoryModel->UseItemAt(SlotIndex))
	{
		return false;
	}

	SynchronizeReplicatedSlotsFromModel();
	OnBackpackStateChanged.Broadcast();
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
	OnBackpackStateChanged.Broadcast();
	return true;
}

bool UBackpackComponent::RestorePersistentSlots(const TArray<FReplicatedInventorySlot>& SavedSlots, int32 SavedCapacity, int32 SavedRevision)
{
	if (!HasServerAuthority() || SavedCapacity < 0 || SavedSlots.Num() != SavedCapacity)
	{
		return false;
	}

	Initialize();
	ReplicatedSlots.Items = SavedSlots;
	for (FReplicatedInventorySlot& Slot : ReplicatedSlots.Items)
	{
		if (Slot.IsEmpty())
		{
			Slot.Clear();
		}
	}
	ReplicatedSlots.MarkArrayDirty();
	Capacity = SavedCapacity;
	Revision = FMath::Max(0, SavedRevision);
	InventoryModel->ApplyReplicatedSlots(ReplicatedSlots.Items, Capacity);
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

AMyPlayerController* UBackpackComponent::GetOwningPlayerController() const
{
	if (const AMyPlayerState* PlayerState = Cast<AMyPlayerState>(GetOwner()))
	{
		return Cast<AMyPlayerController>(PlayerState->GetPlayerController());
	}
	return nullptr;
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
