// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerState.h"
#include"AbilitySystemInterface.h"
#include "Backpack/BackpackPersistence.h"

#include "MyPlayerState.generated.h"

class ULevelUpInfo;
// Forward declarations
class UAbilitySystemComponent;
class UAttributeSet;
class UBackpackComponent;
class UBackpackItemDefinitions;
class ULoadScreenSaveGame;

DECLARE_MULTICAST_DELEGATE_OneParam(FOnPlayerStatChanged, int32 /*StatValue*/)
DECLARE_MULTICAST_DELEGATE_TwoParams(FOnLevelChanged, int32 /*StatValue*/, bool /*bLevelUp*/)

/**
 * 
 */
UCLASS()
class TEST_25D_API AMyPlayerState : public APlayerState, public IAbilitySystemInterface
{
	GENERATED_BODY()

public:
	AMyPlayerState();
	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
	virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override;
	virtual void ClientInitialize(AController* C) override;
	UAttributeSet* GetAttributeSet() const { return AttributeSet; }
	UBackpackComponent* GetBackpackComponent() const { return BackpackComponent; }




	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<ULevelUpInfo> LevelUpInfo;

	UPROPERTY(EditDefaultsOnly, Category = "Backpack")
	TObjectPtr<UBackpackItemDefinitions> BackpackItemDefinitions;

	FOnPlayerStatChanged OnXPChangedDelegate;
	FOnLevelChanged OnLevelChangedDelegate;
	FOnPlayerStatChanged OnAttributePointsChangedDelegate;
	FOnPlayerStatChanged OnSpellPointsChangedDelegate;

	FORCEINLINE int32 GetPlayerLevel() const { return Level; }
	FORCEINLINE int32 GetXP() const { return XP; }
	FORCEINLINE int32 GetAttributePoints() const { return AttributePoints; }
	FORCEINLINE int32 GetSpellPoints() const { return SpellPoints; }

	void AddToXP(int32 InXP);
	void AddToLevel(int32 InLevel);
	void AddToAttributePoints(int32 InPoints);
	void AddToSpellPoints(int32 InPoints);

	void SetXP(int32 InXP);
	void SetLevel(int32 InLevel);
	

	void SetAttributePoints(int32 InPoints);
	void SetSpellPoints(int32 InPoints);

	FBackpackSnapshot ExportBackpackSnapshot() const;
	bool ImportBackpackSnapshot(const FBackpackSnapshot& Snapshot);
	void SetBackpackPersistencePlayerId(const FString& InPlayerId);
	const FString& GetBackpackPersistencePlayerId() const { return BackpackPersistencePlayerId; }
	virtual void CopyProperties(APlayerState* PlayerState) override;
	virtual void OverrideWith(APlayerState* PlayerState) override;
	int32 GetTravelPlayerSlot() const { return TravelPlayerSlot; }
	void SetTravelPlayerSlot(int32 Slot) { TravelPlayerSlot = Slot; }
	void SetTravelProgress(ULoadScreenSaveGame* Progress, float Health, float Mana);
	ULoadScreenSaveGame* GetTravelProgress() const { return TravelProgress; }
	float GetTravelHealth() const { return TravelHealth; }
	float GetTravelMana() const { return TravelMana; }
	void ClearTravelProgress() { TravelProgress = nullptr; }
protected:
	virtual void BeginPlay() override;

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UAbilitySystemComponent> AbilitySystemComponent;

	UPROPERTY()
	TObjectPtr<UAttributeSet> AttributeSet;

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UBackpackComponent> BackpackComponent;

	UPROPERTY()
	FString BackpackPersistencePlayerId;


private:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="Travel", meta=(AllowPrivateAccess="true"))
	int32 TravelPlayerSlot = INDEX_NONE;
	UPROPERTY(Transient)
	TObjectPtr<ULoadScreenSaveGame> TravelProgress;
	UPROPERTY(Transient)
	float TravelHealth = 0;
	UPROPERTY(Transient)
	float TravelMana = 0;

	UPROPERTY(VisibleAnywhere,ReplicatedUsing=OnRep_Level)
	int32 Level=1;

	UPROPERTY(VisibleAnywhere, ReplicatedUsing = OnRep_XP)
	int32 XP = 0;

	UFUNCTION()
	void OnRep_Level(int32 OldLevel);

	UFUNCTION()
	void OnRep_XP(int32 OldXP);



	UPROPERTY(VisibleAnywhere, ReplicatedUsing = OnRep_AttributePoints)
	int32 AttributePoints = 0;

	UPROPERTY(VisibleAnywhere, ReplicatedUsing = OnRep_SpellPoints)
	int32 SpellPoints = 0;


	UFUNCTION()
	void OnRep_AttributePoints(int32 OldAttributePoints);

	UFUNCTION()
	void OnRep_SpellPoints(int32 OldSpellPoints);

};
