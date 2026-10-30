#include "Backpack/ItemDefinition.h"

const FBackpackItemDefEntry* UBackpackItemDefinitions::FindDefinition(const FPrimaryAssetId& ItemDefinitionId) const
{
	if (!ItemDefinitionId.IsValid())
	{
		return nullptr;
	}

	if (EquipmentTable && EquipmentTable->GetRowStruct() == FBackpackItemDefEntry::StaticStruct())
	{
		for (const auto& Pair : EquipmentTable->GetRowMap())
		{
			const auto* Row = reinterpret_cast<const FBackpackItemDefEntry*>(Pair.Value);
			if (Row->ItemDefinitionId == ItemDefinitionId) return Row;
		}
	}
	for (const FBackpackItemDefEntry& Entry : Items)
	{
		if (Entry.ItemDefinitionId == ItemDefinitionId)
		{
			return &Entry;
		}
	}

	return nullptr;
}

const FBackpackItemDefEntry* UBackpackItemDefinitions::FindDefinitionForPickupActor(const UClass* PickupActorClass) const
{
	if (EquipmentTable && EquipmentTable->GetRowStruct() == FBackpackItemDefEntry::StaticStruct())
	{
		for (const auto& Pair : EquipmentTable->GetRowMap())
		{
			const auto* Row = reinterpret_cast<const FBackpackItemDefEntry*>(Pair.Value);
			if (Row->PickupActorClass && PickupActorClass && PickupActorClass->IsChildOf(Row->PickupActorClass)) return Row;
		}
	}
	for (const FBackpackItemDefEntry& Item : Items)
	{
		if (Item.PickupActorClass && PickupActorClass && PickupActorClass->IsChildOf(Item.PickupActorClass))
		{
			return &Item;
		}
	}
	return nullptr;
}
