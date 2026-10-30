// Fill out your copyright notice in the Description page of Project Settings.


#include "Player/MyPlayerState.h"
#include "AbilitySystem/MyAbilitySystemComponent.h"
#include "Backpack/BackpackComponent.h"
#include "Backpack/ItemDefinition.h"
#include "Equipment/EquipmentComponent.h"
#include "Equipment/EquipmentGenerator.h"
#include <Net/UnrealNetwork.h>

#include "AbilitySystem/MyAttributeSet.h"
#include "Game/LoadScreenSaveGame.h"
AMyPlayerState::AMyPlayerState()
{
	//NetUpdateFrequency = 100.f;	
	SetNetUpdateFrequency(100.f);


	AbilitySystemComponent = CreateDefaultSubobject<UMyAbilitySystemComponent>("AbilitySystemComponent");
	AbilitySystemComponent->SetIsReplicated(true);
	AbilitySystemComponent->SetReplicationMode(EGameplayEffectReplicationMode::Mixed);

	AttributeSet = CreateDefaultSubobject<UMyAttributeSet>("AttributeSet");
	BackpackComponent = CreateDefaultSubobject<UBackpackComponent>("BackpackComponent");
	EquipmentComponent = CreateDefaultSubobject<UEquipmentComponent>("EquipmentComponent");

}

void AMyPlayerState::BeginPlay()
{
	Super::BeginPlay();
	BackpackComponent->SetItemDefinitions(BackpackItemDefinitions);

	if (HasAuthority())
	{
		BackpackComponent->Initialize();
	}

}

void AMyPlayerState::ClientInitialize(AController* C)
{
	Super::ClientInitialize(C);
	BackpackComponent->Initialize();
}

void AMyPlayerState::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);
	DOREPLIFETIME(AMyPlayerState, Level);
	DOREPLIFETIME(AMyPlayerState, XP);
	DOREPLIFETIME(AMyPlayerState, AttributePoints);
	DOREPLIFETIME(AMyPlayerState, SpellPoints);
	DOREPLIFETIME(AMyPlayerState, TravelPlayerSlot);
}

UAbilitySystemComponent* AMyPlayerState::GetAbilitySystemComponent() const
{
	return AbilitySystemComponent;
}



void AMyPlayerState::AddToXP(int32 InXP)
{
	XP += InXP;
	OnXPChangedDelegate.Broadcast(XP);
}

void AMyPlayerState::AddToLevel(int32 InLevel)
{
	Level += InLevel;
	OnLevelChangedDelegate.Broadcast(Level, true);
}

void AMyPlayerState::SetXP(int32 InXP)
{
	XP = InXP;
	OnXPChangedDelegate.Broadcast(XP);
}

void AMyPlayerState::SetLevel(int32 InLevel)
{
	Level = InLevel;
	OnLevelChangedDelegate.Broadcast(Level, false);
}

void AMyPlayerState::SetAttributePoints(int32 InPoints)
{
	AttributePoints = InPoints;
	OnAttributePointsChangedDelegate.Broadcast(AttributePoints);
}

void AMyPlayerState::SetSpellPoints(int32 InPoints)
{
	SpellPoints = InPoints;
	OnSpellPointsChangedDelegate.Broadcast(SpellPoints);
}

void AMyPlayerState::OnRep_Level(int32 OldLevel)
{
	OnLevelChangedDelegate.Broadcast(Level, true);
}

void AMyPlayerState::OnRep_XP(int32 OldXP)
{
	OnXPChangedDelegate.Broadcast(XP);
}

void AMyPlayerState::OnRep_AttributePoints(int32 OldAttributePoints)
{
	OnAttributePointsChangedDelegate.Broadcast(AttributePoints);
}

void AMyPlayerState::OnRep_SpellPoints(int32 OldSpellPoints)
{
	OnSpellPointsChangedDelegate.Broadcast(SpellPoints);
}

void AMyPlayerState::AddToAttributePoints(int32 InPoints)
{
	AttributePoints += InPoints;
	OnAttributePointsChangedDelegate.Broadcast(AttributePoints);
}

void AMyPlayerState::AddToSpellPoints(int32 InPoints)
{
	SpellPoints += InPoints;
	OnSpellPointsChangedDelegate.Broadcast(SpellPoints);
}

FBackpackSnapshot AMyPlayerState::ExportBackpackSnapshot() const
{
	FBackpackSnapshot Snapshot;
	if (!IsValid(BackpackComponent))
	{
		return Snapshot;
	}

	Snapshot.Equipment = EquipmentComponent->Slots;
	Snapshot.EquipmentRevision = EquipmentComponent->Revision;
	Snapshot.Capacity = BackpackComponent->GetCapacity();
	Snapshot.Revision = BackpackComponent->GetRevision();
	const TArray<FReplicatedInventorySlot>& ReplicatedSlots = BackpackComponent->GetReplicatedSlots().Items;
	Snapshot.Slots.SetNum(ReplicatedSlots.Num());
	for (int32 SlotIndex = 0; SlotIndex < ReplicatedSlots.Num(); ++SlotIndex)
	{
		Snapshot.Slots[SlotIndex].ItemDefinitionId = ReplicatedSlots[SlotIndex].ItemDefinitionId;
		Snapshot.Slots[SlotIndex].Quantity = ReplicatedSlots[SlotIndex].Quantity;
		Snapshot.Slots[SlotIndex].ItemInstanceId = ReplicatedSlots[SlotIndex].ItemInstanceId;
        Snapshot.Slots[SlotIndex].RollData = ReplicatedSlots[SlotIndex].RollData;
	}
	return Snapshot;
}

bool AMyPlayerState::ImportBackpackSnapshot(const FBackpackSnapshot& Snapshot)
{
	if (!HasAuthority() || !IsValid(BackpackComponent) || Snapshot.Capacity < 0 || Snapshot.Slots.Num() != Snapshot.Capacity)
	{
		return false;
	}

	if (!BackpackComponent->ItemDefinitions && BackpackItemDefinitions) BackpackComponent->SetItemDefinitions(BackpackItemDefinitions);
 if (!EquipmentComponent->ValidateRecords(Snapshot.Equipment)) return false;
 TSet<FGuid> Seen;
 for (const auto& S : Snapshot.Equipment) Seen.Add(S.ItemInstanceId);
 TArray<FReplicatedInventorySlot> ReplicatedSlots;
	ReplicatedSlots.SetNum(Snapshot.Slots.Num());
	for (int32 SlotIndex = 0; SlotIndex < Snapshot.Slots.Num(); ++SlotIndex)
	{
		FReplicatedInventorySlot& ReplicatedSlot = ReplicatedSlots[SlotIndex];
		const FBackpackSnapshotSlot& SavedSlot = Snapshot.Slots[SlotIndex];
        if (!FEquipmentGenerator::ValidateRoll(SavedSlot.RollData) || (SavedSlot.IsEmpty() && SavedSlot.RollData.GenerationVersion != 0)) return false;
        if (SavedSlot.Quantity < 0 || (SavedSlot.ItemDefinitionId.IsValid() != (SavedSlot.Quantity > 0))) return false;
		if (!SavedSlot.IsEmpty())
		{
			ReplicatedSlot.ItemDefinitionId = SavedSlot.ItemDefinitionId;
			ReplicatedSlot.Quantity = SavedSlot.Quantity;
            ReplicatedSlot.RollData = SavedSlot.RollData;
   ReplicatedSlot.ItemInstanceId = SavedSlot.ItemInstanceId.IsValid() ? SavedSlot.ItemInstanceId : FGuid::NewGuid();
   if (Seen.Contains(ReplicatedSlot.ItemInstanceId)) return false;
   Seen.Add(ReplicatedSlot.ItemInstanceId);
   const auto* Def = BackpackComponent->ItemDefinitions ? BackpackComponent->ItemDefinitions->FindDefinition(SavedSlot.ItemDefinitionId) : nullptr;
   if (!FEquipmentGenerator::ValidateRoll(SavedSlot.RollData)) return false;
   if (SavedSlot.RollData.GenerationVersion > 0 && (!Def || !Def->bRandomizedEquipment || SavedSlot.RollData.ProfileId != Def->GenerationProfile)) return false;
   if (Def && Def->bRandomizedEquipment && SavedSlot.RollData.GenerationVersion == 0) return false;
   if (Def && Def->bEquippable && (SavedSlot.Quantity != 1 || Def->bStackable || Def->MaxStack != 1)) return false;
		}
	}
	return EquipmentComponent->RestoreCombined(ReplicatedSlots, Snapshot.Capacity, Snapshot.Revision, Snapshot.Equipment, Snapshot.EquipmentRevision);
}

void AMyPlayerState::SetBackpackPersistencePlayerId(const FString& InPlayerId)
{
	BackpackPersistencePlayerId = InPlayerId;
}

void AMyPlayerState::CopyProperties(APlayerState* PlayerState)
{
	Super::CopyProperties(PlayerState);
	if (AMyPlayerState* DestinationState = Cast<AMyPlayerState>(PlayerState))
	{
		DestinationState->SetBackpackPersistencePlayerId(BackpackPersistencePlayerId);
		DestinationState->ImportBackpackSnapshot(ExportBackpackSnapshot());
		DestinationState->TravelPlayerSlot = TravelPlayerSlot;
		DestinationState->TravelProgress = TravelProgress;
		DestinationState->TravelHealth = TravelHealth;
		DestinationState->TravelMana = TravelMana;
		DestinationState->Level = Level;
		DestinationState->XP = XP;
		DestinationState->AttributePoints = AttributePoints;
		DestinationState->SpellPoints = SpellPoints;
	}
}

void AMyPlayerState::OverrideWith(APlayerState* PlayerState)
{
	Super::OverrideWith(PlayerState);
	if (const AMyPlayerState* SourceState = Cast<AMyPlayerState>(PlayerState))
	{
		SetBackpackPersistencePlayerId(SourceState->GetBackpackPersistencePlayerId());
		ImportBackpackSnapshot(SourceState->ExportBackpackSnapshot());
	}
}

void AMyPlayerState::SetTravelProgress(ULoadScreenSaveGame* Progress, float Health, float Mana)
{
	TravelProgress = Progress;
	TravelHealth = Health;
	TravelMana = Mana;
}
