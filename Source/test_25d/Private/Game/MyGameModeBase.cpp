// Fill out your copyright notice in the Description page of Project Settings.


#include "Game/MyGameModeBase.h"

#include "GameplayEffectTypes.h"
#include "AbilitySystem/Data/CharacterClassInfo.h"
#include "Kismet/GameplayStatics.h"

#include "EngineUtils.h"
#include "test_25d/MyLogChannels.h"
#include "Game/MyGameInstance.h"
#include "Game/LoadScreenSaveGame.h"
#include "GameFramework/PlayerStart.h"
#include "Interface/SaveInterface.h"
#include "Kismet/GameplayStatics.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "UI/ViewModel/MVVM_LoadSlot.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Interface/SaveInterface.h"
#include "Backpack/BackpackComponent.h"
#include "Player/MyPlayerState.h"

AMyGameModeBase::AMyGameModeBase()
	: BackpackPersistenceProvider(MakeUnique<FServerLocalBackpackPersistenceProvider>())
{
}

void AMyGameModeBase::PostLogin(APlayerController* NewPlayer)
{
	FString PlayerId;
	if (!NewPlayer || !PendingLoginPlayerIds.RemoveAndCopyValue(NewPlayer, PlayerId))
	{
		Super::PostLogin(NewPlayer);
		return;
	}

	CompleteBackpackLogin(NewPlayer->GetPlayerState<AMyPlayerState>(), PlayerId);
	Super::PostLogin(NewPlayer);
}

void AMyGameModeBase::PreLogin(const FString& Options, const FString& Address, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage)
{
	Super::PreLogin(Options, Address, UniqueId, ErrorMessage);
	if (!ErrorMessage.IsEmpty()) return;

	FString PlayerId;
	if (!ResolveStablePlayerIdForLogin(Options, UniqueId, PlayerId))
	{
		return;
	}

	BeginBackpackLogin(PlayerId, ErrorMessage);
}

APlayerController* AMyGameModeBase::Login(UPlayer* NewPlayer, ENetRole InRemoteRole, const FString& Portal, const FString& Options, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage)
{
	APlayerController* PlayerController = Super::Login(NewPlayer, InRemoteRole, Portal, Options, UniqueId, ErrorMessage);
	FString PlayerId;
	if (!ResolveStablePlayerIdForLogin(Options, UniqueId, PlayerId) || !PendingSessionLocks.Contains(PlayerId))
	{
		return PlayerController;
	}

	if (!IsValid(PlayerController) || !ErrorMessage.IsEmpty())
	{
		BackpackPersistenceProvider->ReleaseSessionLock(PlayerId);
		PendingSessionLocks.Remove(PlayerId);
		return PlayerController;
	}

	PendingLoginPlayerIds.Add(PlayerController, PlayerId);
	return PlayerController;
}

void AMyGameModeBase::Logout(AController* Exiting)
{
	AMyPlayerState* PlayerState = Exiting ? Exiting->GetPlayerState<AMyPlayerState>() : nullptr;
	FString PlayerId;
	if (TryGetStablePlayerId(PlayerState, PlayerId))
	{
		const FActiveBackpackSession* Session = ActiveBackpackSessions.Find(PlayerId);
		if (Session && Session->PlayerState.Get() == PlayerState)
		{
			PersistBackpack(PlayerId);
			ReleaseBackpackSession(PlayerId);
		}
	}
	Super::Logout(Exiting);
}

void AMyGameModeBase::ProcessServerTravel(const FString& URL, bool bAbsolute)
{
	HandleBackpackTravelPersistence(bUseSeamlessTravel);
	Super::ProcessServerTravel(URL, bAbsolute);
}

void AMyGameModeBase::PostSeamlessTravel()
{
	Super::PostSeamlessTravel();
	if (!HasAuthority() || !GameState) return;

	TArray<AMyPlayerState*> PlayerStates;
	for (APlayerState* CurrentPlayerState : GameState->PlayerArray)
	{
		if (AMyPlayerState* PlayerState = Cast<AMyPlayerState>(CurrentPlayerState)) PlayerStates.Add(PlayerState);
	}
	RestoreSeamlessBackpackSessions(PlayerStates);
}

bool AMyGameModeBase::ResolveStablePlayerIdForLogin(const FString& Options, const FUniqueNetIdRepl& UniqueId, FString& OutPlayerId)
{
	OutPlayerId.Reset();
	if (UniqueId.IsValid())
	{
		OutPlayerId = FString::Printf(TEXT("Online.%s"), *UniqueId.ToString());
	}
#if WITH_EDITOR || UE_BUILD_DEVELOPMENT
	else if (const FString LocalDevelopmentId = UGameplayStatics::ParseOption(Options, TEXT("BackpackPlayerId")); !LocalDevelopmentId.IsEmpty())
	{
		OutPlayerId = FString::Printf(TEXT("LocalDev.%s"), *LocalDevelopmentId);
	}
#endif
	return FServerLocalBackpackPersistenceProvider::IsValidPlayerId(OutPlayerId);
}

bool AMyGameModeBase::TryGetStablePlayerId(const AMyPlayerState* PlayerState, FString& OutPlayerId) const
{
	OutPlayerId.Reset();
	if (!IsValid(PlayerState)) return false;
	OutPlayerId = PlayerState->GetBackpackPersistencePlayerId();
	return FServerLocalBackpackPersistenceProvider::IsValidPlayerId(OutPlayerId);
}

bool AMyGameModeBase::BeginBackpackLogin(const FString& PlayerId, FString& OutError)
{
	OutError.Reset();
	if (!BackpackPersistenceProvider || !FServerLocalBackpackPersistenceProvider::IsValidPlayerId(PlayerId))
	{
		OutError = TEXT("backpack_invalid_identity");
		return false;
	}
	if (!BackpackPersistenceProvider->AcquireSessionLock(PlayerId))
	{
		OutError = TEXT("backpack_duplicate_session");
		return false;
	}
	PendingSessionLocks.Add(PlayerId);
	return true;
}

bool AMyGameModeBase::CompleteBackpackLogin(AMyPlayerState* PlayerState, const FString& PlayerId)
{
	if (!PendingSessionLocks.Contains(PlayerId))
	{
		return false;
	}
	if (!IsValid(PlayerState))
	{
		BackpackPersistenceProvider->ReleaseSessionLock(PlayerId);
		PendingSessionLocks.Remove(PlayerId);
		return false;
	}
	PlayerState->SetBackpackPersistencePlayerId(PlayerId);
	RegisterBackpackSession(PlayerState, PlayerId, true);
	PendingSessionLocks.Remove(PlayerId);
	return true;
}

bool AMyGameModeBase::LoadPersistedBackpackSnapshot(const FString& PlayerId, FBackpackSnapshot& OutSnapshot) const
{
	return BackpackPersistenceProvider && BackpackPersistenceProvider->Load(PlayerId, OutSnapshot);
}

void AMyGameModeBase::HandleBackpackTravelPersistence(bool bSeamlessTravel)
{
	for (const TPair<FString, FActiveBackpackSession>& Session : ActiveBackpackSessions) PersistBackpack(Session.Key);
	if (!bSeamlessTravel)
	{
		TArray<FString> PlayerIds;
		ActiveBackpackSessions.GetKeys(PlayerIds);
		for (const FString& PlayerId : PlayerIds) ReleaseBackpackSession(PlayerId);
	}
}

void AMyGameModeBase::RestoreSeamlessBackpackSessions(const TArray<AMyPlayerState*>& PlayerStates)
{
	for (AMyPlayerState* PlayerState : PlayerStates)
	{
		FString PlayerId;
		if (TryGetStablePlayerId(PlayerState, PlayerId)) RegisterBackpackSession(PlayerState, PlayerId, false);
	}
}

void AMyGameModeBase::RegisterBackpackSession(AMyPlayerState* PlayerState, const FString& PlayerId, bool bLoadSnapshot)
{
	if (!IsValid(PlayerState) || ActiveBackpackSessions.Contains(PlayerId)) return;
	if (bLoadSnapshot)
	{
		FBackpackSnapshot Snapshot;
		if (LoadPersistedBackpackSnapshot(PlayerId, Snapshot)) PlayerState->ImportBackpackSnapshot(Snapshot);
	}

	FActiveBackpackSession Session;
	Session.PlayerState = PlayerState;
	TWeakObjectPtr<AMyGameModeBase> WeakGameMode(this);
	Session.MutationHandle = PlayerState->GetBackpackComponent()->OnBackpackStateChanged.AddLambda([WeakGameMode, PlayerId]()
	{
		if (AMyGameModeBase* GameMode = WeakGameMode.Get()) GameMode->PersistBackpack(PlayerId);
	});
	ActiveBackpackSessions.Add(PlayerId, MoveTemp(Session));
}

void AMyGameModeBase::PersistBackpack(const FString& PlayerId)
{
	const FActiveBackpackSession* Session = ActiveBackpackSessions.Find(PlayerId);
	if (BackpackPersistenceProvider && Session && Session->PlayerState.IsValid())
	{
		BackpackPersistenceProvider->Save(PlayerId, Session->PlayerState->ExportBackpackSnapshot());
	}
}

void AMyGameModeBase::ReleaseBackpackSession(const FString& PlayerId)
{
	if (FActiveBackpackSession* Session = ActiveBackpackSessions.Find(PlayerId))
	{
		if (Session->PlayerState.IsValid()) Session->PlayerState->GetBackpackComponent()->OnBackpackStateChanged.Remove(Session->MutationHandle);
		ActiveBackpackSessions.Remove(PlayerId);
	}
	if (BackpackPersistenceProvider) BackpackPersistenceProvider->ReleaseSessionLock(PlayerId);
}

void AMyGameModeBase::SaveSlotData(UMVVM_LoadSlot* LoadSlot, int32 SlotIndex)
{
	if (UGameplayStatics::DoesSaveGameExist(LoadSlot->GetLoadSlotName(), SlotIndex))
	{
		UGameplayStatics::DeleteGameInSlot(LoadSlot->GetLoadSlotName(), SlotIndex);
	}
	USaveGame* SaveGameObject = UGameplayStatics::CreateSaveGameObject(LoadScreenSaveGameClass);
	ULoadScreenSaveGame* LoadScreenSaveGame = Cast<ULoadScreenSaveGame>(SaveGameObject);
	LoadScreenSaveGame->PlayerName = LoadSlot->GetPlayerName();
	LoadScreenSaveGame->SaveSlotStatus = Taken;
	LoadScreenSaveGame->MapName = LoadSlot->GetMapName();
	LoadScreenSaveGame->MapAssetName = LoadSlot->MapAssetName;
	LoadScreenSaveGame->PlayerStartTag = LoadSlot->PlayerStartTag;

	UGameplayStatics::SaveGameToSlot(LoadScreenSaveGame, LoadSlot->GetLoadSlotName(), SlotIndex);
}

ULoadScreenSaveGame* AMyGameModeBase::GetSaveSlotData(const FString& SlotName, int32 SlotIndex) const
{
	USaveGame* SaveGameObject = nullptr;
	if (UGameplayStatics::DoesSaveGameExist(SlotName, SlotIndex))
	{
		SaveGameObject = UGameplayStatics::LoadGameFromSlot(SlotName, SlotIndex);
	}
	else
	{
		SaveGameObject = UGameplayStatics::CreateSaveGameObject(LoadScreenSaveGameClass);
	}
	ULoadScreenSaveGame* LoadScreenSaveGame = Cast<ULoadScreenSaveGame>(SaveGameObject);
	return LoadScreenSaveGame;
}

void AMyGameModeBase::DeleteSlot(const FString& SlotName, int32 SlotIndex)
{
	if (UGameplayStatics::DoesSaveGameExist(SlotName, SlotIndex))
	{
		UGameplayStatics::DeleteGameInSlot(SlotName, SlotIndex);
	}
}

ULoadScreenSaveGame* AMyGameModeBase::RetrieveInGameSaveData()
{
	UMyGameInstance* MyGameInstance = Cast<UMyGameInstance>(GetGameInstance());

	const FString InGameLoadSlotName = MyGameInstance->LoadSlotName;
	const int32 InGameLoadSlotIndex = MyGameInstance->LoadSlotIndex;

	return GetSaveSlotData(InGameLoadSlotName, InGameLoadSlotIndex);
}

void AMyGameModeBase::SaveInGameProgressData(ULoadScreenSaveGame* SaveObject)
{
	UMyGameInstance* MyGameInstance = Cast<UMyGameInstance>(GetGameInstance());

	const FString InGameLoadSlotName = MyGameInstance->LoadSlotName;
	const int32 InGameLoadSlotIndex = MyGameInstance->LoadSlotIndex;
	MyGameInstance->PlayerStartTag = SaveObject->PlayerStartTag;

	UGameplayStatics::SaveGameToSlot(SaveObject, InGameLoadSlotName, InGameLoadSlotIndex);
}

void AMyGameModeBase::SaveWorldState(UWorld* World, const FString& DestinationMapAssetName) const
{
	FString WorldName = World->GetMapName();
	WorldName.RemoveFromStart(World->StreamingLevelsPrefix);

	UMyGameInstance* MyGI = Cast<UMyGameInstance>(GetGameInstance());
	check(MyGI);

	if (ULoadScreenSaveGame* SaveGame = GetSaveSlotData(MyGI->LoadSlotName, MyGI->LoadSlotIndex))
	{
		if (DestinationMapAssetName != FString(""))
		{
			SaveGame->MapAssetName = DestinationMapAssetName;
			SaveGame->MapName = GetMapNameFromMapAssetName(DestinationMapAssetName);
		}

		if (!SaveGame->HasMap(WorldName))
		{
			FSavedMap NewSavedMap;
			NewSavedMap.MapAssetName = WorldName;
			SaveGame->SavedMaps.Add(NewSavedMap);
		}

		FSavedMap SavedMap = SaveGame->GetSavedMapWithMapName(WorldName);
		SavedMap.SavedActors.Empty(); 

		for (FActorIterator It(World); It; ++It)
		{
			AActor* Actor = *It;
				
			if (!IsValid(Actor) || !Actor->Implements<USaveInterface>()) continue;

			FSavedActor SavedActor;
			SavedActor.ActorName = Actor->GetFName();
			SavedActor.Transform = Actor->GetTransform();

			FMemoryWriter MemoryWriter(SavedActor.Bytes);

			FObjectAndNameAsStringProxyArchive Archive(MemoryWriter, true);
			Archive.ArIsSaveGame = true;

			Actor->Serialize(Archive);

			SavedMap.SavedActors.AddUnique(SavedActor);
		}

		for (FSavedMap& MapToReplace : SaveGame->SavedMaps)
		{
			if (MapToReplace.MapAssetName == WorldName)
			{
				MapToReplace = SavedMap;
			}
		}
		UGameplayStatics::SaveGameToSlot(SaveGame, MyGI->LoadSlotName, MyGI->LoadSlotIndex);
	}
}

void AMyGameModeBase::LoadWorldState(UWorld* World) const
{
	FString WorldName = World->GetMapName();
	WorldName.RemoveFromStart(World->StreamingLevelsPrefix);

	UMyGameInstance* MyGI = Cast<UMyGameInstance>(GetGameInstance());
	check(MyGI);

	if (UGameplayStatics::DoesSaveGameExist(MyGI->LoadSlotName, MyGI->LoadSlotIndex))
	{

		ULoadScreenSaveGame* SaveGame = Cast<ULoadScreenSaveGame>(UGameplayStatics::LoadGameFromSlot(MyGI->LoadSlotName, MyGI->LoadSlotIndex));
		if (SaveGame == nullptr)
		{
			UE_LOG(LogMyChannel, Error, TEXT("Failed to load slot"));
			return;
		}

		for (FActorIterator It(World); It; ++It)
		{
			AActor* Actor = *It;

			if (!Actor->Implements<USaveInterface>()) continue;

			for (FSavedActor SavedActor : SaveGame->GetSavedMapWithMapName(WorldName).SavedActors)
			{
				if (SavedActor.ActorName == Actor->GetFName())
				{
					if (ISaveInterface::Execute_ShouldLoadTransform(Actor))
					{
						Actor->SetActorTransform(SavedActor.Transform);
					}

					FMemoryReader MemoryReader(SavedActor.Bytes);

					FObjectAndNameAsStringProxyArchive Archive(MemoryReader, true);
					Archive.ArIsSaveGame = true;
					Actor->Serialize(Archive); 

					ISaveInterface::Execute_LoadActor(Actor);
				}
			}
		}
	}
}

void AMyGameModeBase::TravelToMap(UMVVM_LoadSlot* Slot)
{
	const FString SlotName = Slot->GetLoadSlotName();
	const int32 SlotIndex = Slot->SlotIndex;

	UGameplayStatics::OpenLevelBySoftObjectPtr(Slot, Maps.FindChecked(Slot->GetMapName()));
}

FString AMyGameModeBase::GetMapNameFromMapAssetName(const FString& MapAssetName) const
{
	for (auto& Map : Maps)
	{
		if (Map.Value.ToSoftObjectPath().GetAssetName() == MapAssetName)
		{
			return Map.Key;
		}
	}
	return FString();
}

AActor* AMyGameModeBase::ChoosePlayerStart_Implementation(AController* Player)
{
	UMyGameInstance* MyGameInstance = Cast<UMyGameInstance>(GetGameInstance());

	TArray<AActor*> Actors;
	UGameplayStatics::GetAllActorsOfClass(GetWorld(), APlayerStart::StaticClass(), Actors);
	if (Actors.Num() > 0)
	{
		AActor* SelectedActor = Actors[0];
		for (AActor* Actor : Actors)
		{
			if (APlayerStart* PlayerStart = Cast<APlayerStart>(Actor))
			{
				if (PlayerStart->PlayerStartTag == MyGameInstance->PlayerStartTag)
				{
					SelectedActor = PlayerStart;
					break;
				}
			}
		}
		return SelectedActor;
	}
	return nullptr;
}

void AMyGameModeBase::PlayerDied(ACharacter* DeadCharacter)
{
	if (IsValid(DeadCharacter))
	{
		if (AMyPlayerState* PlayerState = DeadCharacter->GetPlayerState<AMyPlayerState>())
		{
			FString PlayerId;
			if (TryGetStablePlayerId(PlayerState, PlayerId)) PersistBackpack(PlayerId);
		}
	}

	ULoadScreenSaveGame* SaveGame = RetrieveInGameSaveData();
	if (!IsValid(SaveGame)) return;

	UGameplayStatics::OpenLevel(DeadCharacter, FName(SaveGame->MapAssetName));
}

void AMyGameModeBase::BeginPlay()
{
	Super::BeginPlay();
	Maps.Add(DefaultMapName, DefaultMap);
}
