#pragma once

#include "CoreMinimal.h"
#include "Net/Serialization/FastArraySerializer.h"
#include "ReplicatedInventory.generated.h"

USTRUCT(BlueprintType)
struct FReplicatedInventorySlot : public FFastArraySerializerItem
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly)
	FPrimaryAssetId ItemDefinitionId;

	UPROPERTY(BlueprintReadOnly)
	int32 Quantity = 0;

	bool IsEmpty() const
	{
		return !ItemDefinitionId.IsValid() || Quantity <= 0;
	}

	void Clear()
	{
		ItemDefinitionId = FPrimaryAssetId();
		Quantity = 0;
	}
};

USTRUCT()
struct FReplicatedInventoryList : public FFastArraySerializer
{
	GENERATED_BODY()

	UPROPERTY()
	TArray<FReplicatedInventorySlot> Items;

	bool NetDeltaSerialize(FNetDeltaSerializeInfo& DeltaParams)
	{
		return FastArrayDeltaSerialize<FReplicatedInventorySlot, FReplicatedInventoryList>(Items, DeltaParams, *this);
	}
};

template<>
struct TStructOpsTypeTraits<FReplicatedInventoryList> : public TStructOpsTypeTraitsBase2<FReplicatedInventoryList>
{
	enum
	{
		WithNetDeltaSerializer = true,
	};
};
