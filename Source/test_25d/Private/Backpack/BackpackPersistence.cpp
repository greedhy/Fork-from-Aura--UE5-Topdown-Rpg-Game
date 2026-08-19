#include "Backpack/BackpackPersistence.h"

#include "Kismet/GameplayStatics.h"
#include "Misc/ScopeLock.h"

FCriticalSection FServerLocalBackpackPersistenceProvider::SessionLockGuard;
TSet<FString> FServerLocalBackpackPersistenceProvider::ActiveSessionLocks;

bool FServerLocalBackpackPersistenceProvider::Load(const FString& PlayerId, FBackpackSnapshot& OutSnapshot) const
{
	OutSnapshot = FBackpackSnapshot();
	if (!IsValidPlayerId(PlayerId) || !UGameplayStatics::DoesSaveGameExist(MakeSaveSlotName(PlayerId), 0)) return false;
	const UBackpackPersistenceSaveGame* SaveGame = Cast<UBackpackPersistenceSaveGame>(UGameplayStatics::LoadGameFromSlot(MakeSaveSlotName(PlayerId), 0));
	if (!IsValid(SaveGame) || SaveGame->PlayerId != PlayerId) return false;
	OutSnapshot = SaveGame->Snapshot;
	return true;
}

bool FServerLocalBackpackPersistenceProvider::Save(const FString& PlayerId, const FBackpackSnapshot& Snapshot)
{
	if (!IsValidPlayerId(PlayerId) || Snapshot.Capacity < 0 || Snapshot.Slots.Num() != Snapshot.Capacity) return false;
	UBackpackPersistenceSaveGame* SaveGame = Cast<UBackpackPersistenceSaveGame>(UGameplayStatics::CreateSaveGameObject(UBackpackPersistenceSaveGame::StaticClass()));
	if (!IsValid(SaveGame)) return false;
	SaveGame->PlayerId = PlayerId;
	SaveGame->Snapshot = Snapshot;
	return UGameplayStatics::SaveGameToSlot(SaveGame, MakeSaveSlotName(PlayerId), 0);
}

bool FServerLocalBackpackPersistenceProvider::AcquireSessionLock(const FString& PlayerId)
{
	if (!IsValidPlayerId(PlayerId)) return false;
	FScopeLock Lock(&SessionLockGuard);
	if (ActiveSessionLocks.Contains(PlayerId)) return false;
	ActiveSessionLocks.Add(PlayerId);
	return true;
}

void FServerLocalBackpackPersistenceProvider::ReleaseSessionLock(const FString& PlayerId)
{
	if (!IsValidPlayerId(PlayerId)) return;
	FScopeLock Lock(&SessionLockGuard);
	ActiveSessionLocks.Remove(PlayerId);
}

bool FServerLocalBackpackPersistenceProvider::IsValidPlayerId(const FString& PlayerId)
{
	if (PlayerId.IsEmpty() || PlayerId.Len() > 128) return false;
	for (const TCHAR Character : PlayerId)
	{
		if (!FChar::IsAlnum(Character) && Character != TEXT('_') && Character != TEXT('-') && Character != TEXT('.') && Character != TEXT(':')) return false;
	}
	return true;
}

FString FServerLocalBackpackPersistenceProvider::MakeSaveSlotName(const FString& PlayerId)
{
	FString SaveSlotName(TEXT("Backpack_"));
	for (const TCHAR Character : PlayerId) SaveSlotName += FString::Printf(TEXT("%04X"), static_cast<uint32>(Character));
	return SaveSlotName;
}
