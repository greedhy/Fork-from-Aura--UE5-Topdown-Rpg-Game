// Fill out your copyright notice in the Description page of Project Settings.


#include "Player/MyPlayerState.h"
#include "AbilitySystem/MyAbilitySystemComponent.h"
#include "Backpack/BackpackComponent.h"
#include <Net/UnrealNetwork.h>

#include "AbilitySystem/MyAttributeSet.h"
AMyPlayerState::AMyPlayerState()
{
	//NetUpdateFrequency = 100.f;	
	SetNetUpdateFrequency(100.f);


	AbilitySystemComponent = CreateDefaultSubobject<UMyAbilitySystemComponent>("AbilitySystemComponent");
	AbilitySystemComponent->SetIsReplicated(true);
	AbilitySystemComponent->SetReplicationMode(EGameplayEffectReplicationMode::Mixed);

	AttributeSet = CreateDefaultSubobject<UMyAttributeSet>("AttributeSet");
	BackpackComponent = CreateDefaultSubobject<UBackpackComponent>("BackpackComponent");

}

void AMyPlayerState::BeginPlay()
{
	Super::BeginPlay();

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

	Snapshot.Capacity = BackpackComponent->GetCapacity();
	Snapshot.Revision = BackpackComponent->GetRevision();
	const TArray<FReplicatedInventorySlot>& ReplicatedSlots = BackpackComponent->GetReplicatedSlots().Items;
	Snapshot.Slots.SetNum(ReplicatedSlots.Num());
	for (int32 SlotIndex = 0; SlotIndex < ReplicatedSlots.Num(); ++SlotIndex)
	{
		Snapshot.Slots[SlotIndex].ItemDefinitionId = ReplicatedSlots[SlotIndex].ItemDefinitionId;
		Snapshot.Slots[SlotIndex].Quantity = ReplicatedSlots[SlotIndex].Quantity;
	}
	return Snapshot;
}

bool AMyPlayerState::ImportBackpackSnapshot(const FBackpackSnapshot& Snapshot)
{
	if (!HasAuthority() || !IsValid(BackpackComponent) || Snapshot.Capacity < 0 || Snapshot.Slots.Num() != Snapshot.Capacity)
	{
		return false;
	}

	TArray<FReplicatedInventorySlot> ReplicatedSlots;
	ReplicatedSlots.SetNum(Snapshot.Slots.Num());
	for (int32 SlotIndex = 0; SlotIndex < Snapshot.Slots.Num(); ++SlotIndex)
	{
		FReplicatedInventorySlot& ReplicatedSlot = ReplicatedSlots[SlotIndex];
		const FBackpackSnapshotSlot& SavedSlot = Snapshot.Slots[SlotIndex];
		if (!SavedSlot.IsEmpty())
		{
			ReplicatedSlot.ItemDefinitionId = SavedSlot.ItemDefinitionId;
			ReplicatedSlot.Quantity = SavedSlot.Quantity;
		}
	}
	return BackpackComponent->RestorePersistentSlots(ReplicatedSlots, Snapshot.Capacity, Snapshot.Revision);
}

void AMyPlayerState::CopyProperties(APlayerState* PlayerState)
{
	Super::CopyProperties(PlayerState);
	if (AMyPlayerState* DestinationState = Cast<AMyPlayerState>(PlayerState))
	{
		DestinationState->ImportBackpackSnapshot(ExportBackpackSnapshot());
	}
}

void AMyPlayerState::OverrideWith(APlayerState* PlayerState)
{
	Super::OverrideWith(PlayerState);
	if (const AMyPlayerState* SourceState = Cast<AMyPlayerState>(PlayerState))
	{
		ImportBackpackSnapshot(SourceState->ExportBackpackSnapshot());
	}
}
