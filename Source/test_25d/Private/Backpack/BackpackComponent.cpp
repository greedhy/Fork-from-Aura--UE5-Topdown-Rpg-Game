// Fill out your copyright notice in the Description page of Project Settings.


#include "Backpack/BackpackComponent.h"
#include "Equipment/EquipmentComponent.h"
#include "Equipment/EquipmentGenerator.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ItemDefinition.h"
#include "Backpack/WorldPickupComponent.h"
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
	InventoryModel->SetItemDefinitions(ItemDefinitions);
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
	if (!HasServerAuthority() || bEquipmentMutation || !IsValid(Definition) || Quantity <= 0)
	{
		return Result;
	}

	Initialize();
 if (const auto* Entry=InventoryModel->FindItemDefinition(Definition->GetPrimaryAssetId()); Entry && Entry->bRandomizedEquipment)
  return TryAddItem(Definition->GetPrimaryAssetId(), Quantity);
	Result = InventoryModel->TryAddItem(Definition, Quantity);
	if (Result.bSucceeded)
	{
		SynchronizeReplicatedSlotsFromModel();
		OnBackpackStateChanged.Broadcast();
	}
	return Result;
}

FInventoryAddResult UBackpackComponent::TryAddItem(const FPrimaryAssetId& ItemDefinitionId, int32 Quantity)
{
	FInventoryAddResult Result;
	if (!HasServerAuthority() || bEquipmentMutation || !ItemDefinitionId.IsValid() || Quantity <= 0)
	{
		return Result;
	}

	Initialize();
 const auto* Definition = InventoryModel->FindItemDefinition(ItemDefinitionId);
 if (Definition && Definition->bRandomizedEquipment)
 {
  Result.RemainingQuantity = Quantity;
  while (Result.RemainingQuantity > 0 && InventoryModel->Slots.ContainsByPredicate([](const FInventorySlot& S){return S.IsEmpty();}))
  {
   FEquipmentRollData Roll; FString Error;
   if (!FEquipmentGenerator::Generate(*ItemDefinitions, *Definition, 0, FMath::Rand(), Roll, Error)) break;
   if (!TryAddExistingItem(ItemDefinitionId, FGuid::NewGuid(), Roll)) break;
   ++Result.AcceptedQuantity; --Result.RemainingQuantity;
  }
  Result.bSucceeded = Result.AcceptedQuantity > 0; return Result;
 }
	Result = InventoryModel->TryAddItem(ItemDefinitionId, Quantity);
	if (Result.bSucceeded)
	{
		SynchronizeReplicatedSlotsFromModel();
		OnBackpackStateChanged.Broadcast();
	}
	return Result;
}

bool UBackpackComponent::TryAddExistingItem(const FPrimaryAssetId& Id, const FGuid& InstanceId, const FEquipmentRollData& RollData)
{
 if (!HasServerAuthority() || bEquipmentMutation || !InstanceId.IsValid()) return false;
 Initialize();
 if (const auto* Equipment = GetOwner()->FindComponentByClass<UEquipmentComponent>()) if (Equipment->ContainsInstance(InstanceId)) return false;
 const auto* Def = InventoryModel->FindItemDefinition(Id);
 if (!Def || !Def->bEquippable || Def->bStackable || Def->MaxStack != 1 ||
     !FEquipmentGenerator::ValidateRoll(RollData) || Def->bRandomizedEquipment != (RollData.GenerationVersion > 0) ||
     (Def->bRandomizedEquipment && RollData.ProfileId != Def->GenerationProfile)) return false;
 for (const auto& Slot : InventoryModel->Slots) if (Slot.ItemInstanceId == InstanceId) return false;
 for (auto& Slot : InventoryModel->Slots) if (Slot.IsEmpty())
 {
  Slot.ItemDefinitionId = Id; Slot.ItemInstanceId = InstanceId; Slot.Quantity = 1; Slot.RollData = RollData;
  SynchronizeReplicatedSlotsFromModel();
  InventoryModel->OnInventoryUpdated.Broadcast(InventoryModel->Slots);
  OnBackpackStateChanged.Broadcast(); return true;
 }
 return false;
}

void UBackpackComponent::SetItemDefinitions(UBackpackItemDefinitions* InItemDefinitions)
{
	ItemDefinitions = InItemDefinitions;
	if (IsValid(InventoryModel))
	{
		InventoryModel->SetItemDefinitions(ItemDefinitions);
	}
}

void UBackpackComponent::ConfigureSpawnedPickupActor(AActor* PickupActor)
{
	UWorldPickupComponent::ConfigureOwnerForNetworkedPickup(PickupActor);
}

bool UBackpackComponent::DropWholeStack(int32 SlotIndex, const FVector& SpawnLocation)
{
	if (!HasServerAuthority() || bEquipmentMutation)
	{
		return false;
	}

	Initialize();
	const TArray<FInventorySlot>& Slots = InventoryModel->GetSlots();
	if (!Slots.IsValidIndex(SlotIndex) || Slots[SlotIndex].IsEmpty())
	{
		return false;
	}

	const FInventorySlot StackToDrop = Slots[SlotIndex];
	const FBackpackItemDefEntry* Definition = InventoryModel->FindItemDefinition(StackToDrop.ItemDefinitionId);
	if (!Definition || !Definition->PickupActorClass)
	{
		return false;
	}

	const FTransform SpawnTransform(FRotator::ZeroRotator, SpawnLocation);
 AActor* DroppedActor = GetWorld()->SpawnActorDeferred<AActor>(Definition->PickupActorClass, SpawnTransform);
 if (!DroppedActor) return false;
 // Blueprint-added pickup components exist after construction. Keep overlaps disabled until configured.
 DroppedActor->SetActorEnableCollision(false);
 DroppedActor->FinishSpawning(SpawnTransform);
	ConfigureSpawnedPickupActor(DroppedActor);
	UWorldPickupComponent* DroppedPickup = IsValid(DroppedActor) ? DroppedActor->FindComponentByClass<UWorldPickupComponent>() : nullptr;
	if (!IsValid(DroppedPickup))
	{
		if (IsValid(DroppedActor)) DroppedActor->Destroy();
		return false;
	}
	DroppedPickup->ItemDefinitions = ItemDefinitions;
	DroppedPickup->ConfigurePickup(StackToDrop.ItemDefinitionId, StackToDrop.Quantity, true, &StackToDrop.RollData);
	DroppedPickup->ItemInstanceId = StackToDrop.ItemInstanceId;
 DroppedPickup->RollData = StackToDrop.RollData;
	InventoryModel->Slots[SlotIndex].Clear();
	SynchronizeReplicatedSlotsFromModel();
	DroppedActor->SetActorEnableCollision(true);
	InventoryModel->OnInventoryUpdated.Broadcast(InventoryModel->Slots);
	OnBackpackStateChanged.Broadcast();
	return true;
}

bool UBackpackComponent::SwapSlots(int32 IndexA, int32 IndexB)
{
	if (!HasServerAuthority() || bEquipmentMutation)
	{
		UE_LOG(LogTemp, Warning, TEXT("[BackpackDrag] Server rejected swap %d -> %d: component has no authority."), IndexA, IndexB);
		return false;
	}

	Initialize();
	if (!InventoryModel->SwapSlots(IndexA, IndexB))
	{
		UE_LOG(LogTemp, Warning, TEXT("[BackpackDrag] Server rejected swap %d -> %d: model rejected the indices."), IndexA, IndexB);
		return false;
	}

	SynchronizeReplicatedSlotsFromModel();
	OnBackpackStateChanged.Broadcast();
	UE_LOG(LogTemp, Log, TEXT("[BackpackDrag] Server completed swap: %d <-> %d."), IndexA, IndexB);
	return true;
}

bool UBackpackComponent::TryUseItemForPawn(int32 SlotIndex, APawn* Pawn)
{
	if (!HasServerAuthority() || bEquipmentMutation || !IsValid(Pawn))
	{
		return false;
	}

	Initialize();
	const TArray<FInventorySlot>& Slots = InventoryModel->GetSlots();
	if (!Slots.IsValidIndex(SlotIndex) || Slots[SlotIndex].IsEmpty())
	{
		return false;
	}

	const FBackpackItemDefEntry* CatalogDefinition = InventoryModel->FindItemDefinition(Slots[SlotIndex].ItemDefinitionId);
	UItemDefinition* LegacyDefinition = InventoryModel->ItemDefinitions.FindRef(Slots[SlotIndex].ItemDefinitionId);
	const bool bUsesCatalogDefinition = CatalogDefinition != nullptr;
	const bool bCanUse = bUsesCatalogDefinition ? !CatalogDefinition->bEquippable && CatalogDefinition->bUsable && CatalogDefinition->UseEffect : IsValid(LegacyDefinition) && LegacyDefinition->bUsable && LegacyDefinition->UseEffect;
	if (!bCanUse)
	{
		return false;
	}

	UAbilitySystemComponent* TargetAbilitySystem = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Pawn);
	if (!IsValid(TargetAbilitySystem))
	{
		return false;
	}

	FGameplayEffectContextHandle EffectContext = TargetAbilitySystem->MakeEffectContext();
	EffectContext.AddSourceObject(bUsesCatalogDefinition ? static_cast<UObject*>(ItemDefinitions) : static_cast<UObject*>(LegacyDefinition));
	const TSubclassOf<UGameplayEffect> UseEffect = bUsesCatalogDefinition ? CatalogDefinition->UseEffect : LegacyDefinition->UseEffect;
	const FGameplayEffectSpecHandle EffectSpec = TargetAbilitySystem->MakeOutgoingSpec(UseEffect, 1.f, EffectContext);
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
	if (!HasServerAuthority() || bEquipmentMutation)
	{
		return false;
	}

	const int32 ClampedCapacity = FMath::Max(0, NewCapacity);
	Initialize();
	for (int32 I = ClampedCapacity; I < InventoryModel->GetSlots().Num(); ++I)
	{
		const auto& Slot = InventoryModel->GetSlots()[I];
		const auto* Def = InventoryModel->FindItemDefinition(Slot.ItemDefinitionId);
		if (!Slot.IsEmpty() && Def && Def->bEquippable) return false;
	}
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
	if (!HasServerAuthority() || bEquipmentMutation || SavedCapacity < 0 || SavedSlots.Num() != SavedCapacity)
	{
		return false;
	}

 Initialize();
 TSet<FGuid> Seen;
 const auto* Equipment = GetOwner()->FindComponentByClass<UEquipmentComponent>();
 for (const auto& Item : SavedSlots)
 {
  const auto* Def=InventoryModel->FindItemDefinition(Item.ItemDefinitionId);
  if (!FEquipmentGenerator::ValidateForDefinition(Def,Item.RollData)) return false;
  if (Item.IsEmpty()) { if (Item.RollData.GenerationVersion != 0) return false; continue; }
  if (Def && Def->bEquippable && (Item.Quantity!=1 || !Item.ItemInstanceId.IsValid())) return false;
  if (Item.ItemInstanceId.IsValid() && (Seen.Contains(Item.ItemInstanceId) || (Equipment && Equipment->ContainsInstance(Item.ItemInstanceId)))) return false;
  if (Item.ItemInstanceId.IsValid()) Seen.Add(Item.ItemInstanceId);
 }
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
		if (ReplicatedSlot.ItemDefinitionId == ModelSlot.ItemDefinitionId && ReplicatedSlot.Quantity == ModelSlot.Quantity && ReplicatedSlot.ItemInstanceId == ModelSlot.ItemInstanceId && ReplicatedSlot.RollData == ModelSlot.RollData)
		{
			continue;
		}

		ReplicatedSlot.ItemDefinitionId = ModelSlot.ItemDefinitionId;
		ReplicatedSlot.Quantity = ModelSlot.Quantity;
		ReplicatedSlot.ItemInstanceId = ModelSlot.ItemInstanceId;
        ReplicatedSlot.RollData = ModelSlot.RollData;
		ReplicatedSlots.MarkItemDirty(ReplicatedSlot);
		bChanged = true;
	}

	if (bChanged)
	{
		++Revision;
	}
}
