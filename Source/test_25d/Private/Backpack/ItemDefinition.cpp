#include "Backpack/ItemDefinition.h"

const FBackpackItemDefEntry* UBackpackItemDefinitions::FindDefinition(const FPrimaryAssetId& ItemDefinitionId) const
{
	if (!ItemDefinitionId.IsValid())
	{
		return nullptr;
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
	for (const FBackpackItemDefEntry& Item : Items)
	{
		if (Item.PickupActorClass && PickupActorClass && PickupActorClass->IsChildOf(Item.PickupActorClass))
		{
			return &Item;
		}
	}
	return nullptr;
}
