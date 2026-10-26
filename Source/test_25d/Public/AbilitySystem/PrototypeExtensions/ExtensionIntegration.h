#pragma once
#include "CoreMinimal.h"
#include "PureMass/PureMassPlayerCharacter.h"
#include "PureMass/PureMassGameMode.h"
#include "UI/HUD/MyHUD.h"
#include "ExtensionIntegration.generated.h"

UCLASS()
class TEST_25D_API AExtensionPlayerCharacter : public APureMassPlayerCharacter
{
    GENERATED_BODY()
public:
    AExtensionPlayerCharacter();
    virtual void PossessedBy(AController* Controller) override;
    virtual void SaveProgress_Implementation(const FName& CheckpointTag) override;
    UPROPERTY(EditDefaultsOnly, Category="Abilities") TArray<TSubclassOf<class UGameplayAbility>> PersistentStartupPassives;
};
UCLASS()
class TEST_25D_API AExtensionGameMode : public APureMassGameMode
{
    GENERATED_BODY()
public:
    virtual void InitGame(const FString& MapName,const FString& Options,FString& Error) override;
};
/** Appends extension entries to constructed menu instances only in the opt-in HUD. */
UCLASS()
class TEST_25D_API AExtensionHUD : public AMyHUD
{
    GENERATED_BODY()
public:
    AExtensionHUD();
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<class UAbilityInfo> ExtensionCatalog;
    UPROPERTY() TMap<TObjectPtr<class UDataTable>, TObjectPtr<class UDataTable>> DescriptionStyles;
    TSet<TWeakObjectPtr<class UPrototypeSpellTree>> PopulatedTrees;
    TSet<TWeakObjectPtr<class URichTextBlock>> StyledDescriptions;
    TWeakObjectPtr<class UMyAbilitySystemComponent> DisplayedASC;
    TWeakObjectPtr<APawn> DisplayedPawn;
    uint32 DisplayedAbilityHash = 0;
};
