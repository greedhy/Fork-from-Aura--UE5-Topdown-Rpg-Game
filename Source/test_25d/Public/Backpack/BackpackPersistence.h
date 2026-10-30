#pragma once

#include "CoreMinimal.h"
#include "Equipment/EquipmentRollTypes.h"
#include "GameFramework/SaveGame.h"
#include "Equipment/EquipmentComponent.h"
#include "BackpackPersistence.generated.h"

USTRUCT(BlueprintType)
struct FBackpackSnapshotSlot
{
	GENERATED_BODY()

	UPROPERTY(SaveGame, BlueprintReadOnly)
	FPrimaryAssetId ItemDefinitionId;

	UPROPERTY(SaveGame, BlueprintReadOnly)
	FGuid ItemInstanceId;
 UPROPERTY(SaveGame, BlueprintReadOnly) FEquipmentRollData RollData;

	UPROPERTY(SaveGame, BlueprintReadOnly)
	int32 Quantity = 0;

	bool IsEmpty() const { return !ItemDefinitionId.IsValid() || Quantity <= 0; }
	void Clear() { RollData = FEquipmentRollData(); ItemInstanceId.Invalidate(); ItemDefinitionId = FPrimaryAssetId(); Quantity = 0; }
};

USTRUCT(BlueprintType)
struct FBackpackSnapshot
{
	GENERATED_BODY()

	UPROPERTY(SaveGame, BlueprintReadOnly)
	TArray<FBackpackSnapshotSlot> Slots;
	UPROPERTY(SaveGame, BlueprintReadOnly)
	TArray<FEquipmentSlot> Equipment;
	UPROPERTY(SaveGame, BlueprintReadOnly)
	int32 EquipmentRevision = 0;

	UPROPERTY(SaveGame, BlueprintReadOnly)
	int32 Capacity = 0;

	UPROPERTY(SaveGame, BlueprintReadOnly)
	int32 Revision = 0;
};

UCLASS()
class TEST_25D_API UBackpackPersistenceSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	UPROPERTY(SaveGame)
	FString PlayerId;

	UPROPERTY(SaveGame)
	FBackpackSnapshot Snapshot;
};

class TEST_25D_API IBackpackPersistenceProvider
{
public:
	virtual ~IBackpackPersistenceProvider() = default;
	virtual bool Load(const FString& PlayerId, FBackpackSnapshot& OutSnapshot) const = 0;
	virtual bool Save(const FString& PlayerId, const FBackpackSnapshot& Snapshot) = 0;
	virtual bool AcquireSessionLock(const FString& PlayerId) = 0;
	virtual void ReleaseSessionLock(const FString& PlayerId) = 0;
};

class TEST_25D_API FServerLocalBackpackPersistenceProvider final : public IBackpackPersistenceProvider
{
public:
	virtual bool Load(const FString& PlayerId, FBackpackSnapshot& OutSnapshot) const override;
	virtual bool Save(const FString& PlayerId, const FBackpackSnapshot& Snapshot) override;
	virtual bool AcquireSessionLock(const FString& PlayerId) override;
	virtual void ReleaseSessionLock(const FString& PlayerId) override;

	static bool IsValidPlayerId(const FString& PlayerId);

private:
	static FString MakeSaveSlotName(const FString& PlayerId);

	static FCriticalSection SessionLockGuard;
	static TSet<FString> ActiveSessionLocks;
};
