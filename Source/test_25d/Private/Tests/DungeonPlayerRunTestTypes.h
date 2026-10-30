#pragma once
#include "CoreMinimal.h"
#include "Roguelike/DungeonPlayerCharacter.h"
#include "Player/MyPlayerState.h"
#include "AbilitySystem/Ability/MyPassiveAbility.h"
#include "DungeonPlayerRunTestTypes.generated.h"

UCLASS(Transient, NotBlueprintable)
class ADungeonPlayerRunTestPawn : public ADungeonPlayerCharacter
{
    GENERATED_BODY()
public:
    void AttachState(AMyPlayerState* State)
    {
        SetPlayerState(State);
        AbilitySystemComponent = State->GetAbilitySystemComponent();
        AttributeSet = State->GetAttributeSet();
        AbilitySystemComponent->InitAbilityActorInfo(State, this);
    }
    UFUNCTION() void CountDeath(AActor* DeadActor) { ++Deaths; }
    void SetTestRole(ENetRole InRole) { SetRole(InRole); }
    int32 Deaths = 0;
};

UCLASS(Transient, NotBlueprintable)
class UDungeonPlayerRunTestPassive : public UMyPassiveAbility
{
    GENERATED_BODY()
public:
    UDungeonPlayerRunTestPassive()
    {
        InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
        NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::ServerOnly;
    }
};

UCLASS(Transient, NotBlueprintable)
class UDungeonPlayerRunTestToggle : public UDungeonPlayerRunTestPassive
{
    GENERATED_BODY()
public:
    virtual bool IsInputToggleAbility() const override { return true; }
};

UCLASS(Transient, NotBlueprintable)
class UDungeonPlayerRunTestTaggedAbility : public UMyGameplayAbility
{
    GENERATED_BODY()
public:
    UDungeonPlayerRunTestTaggedAbility()
    {
        InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
        NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::ServerOnly;
        SetAssetTags(FGameplayTagContainer(FGameplayTag::RequestGameplayTag(TEXT("Abilities.Attack"))));
    }
};
