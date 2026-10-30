#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Ability/MyDamageGameplayAbility.h"
#include "GameplayEffect.h"
#include "StoneGolem/StoneGolemConfig.h"
#include "StoneGolemAbility.generated.h"
class AStoneGolemCharacter;

UCLASS()
class TEST_25D_API UStoneGolemCooldownEffect : public UGameplayEffect
{
    GENERATED_BODY()
public: UStoneGolemCooldownEffect();
};

UCLASS(Abstract)
class TEST_25D_API UStoneGolemAttackAbility : public UMyDamageGameplayAbility
{
    GENERATED_BODY()
public:
    UStoneGolemAttackAbility();
    UPROPERTY(EditDefaultsOnly,BlueprintReadOnly,Category="StoneGolem") TObjectPtr<UStoneGolemAttackConfig> AttackConfig;
    virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        const FGameplayTagContainer* Source=nullptr,const FGameplayTagContainer* Target=nullptr,FGameplayTagContainer* Relevant=nullptr) const override;
    virtual bool CheckCooldown(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayTagContainer* Relevant=nullptr) const override;
    virtual void ApplyCooldown(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo Activation) const override;
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation,const FGameplayEventData* Event) override;
    virtual void EndAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation,bool Replicate,bool Cancelled) override;
    void GatherTargets(TArray<AActor*>& Out) const;
protected:
    FGameplayTag CooldownIdentity;
private:
    void Advance();
    void Abort();
    bool UpdateAim();
    void ResolveHit();
    UPROPERTY() FStoneGolemAttackTuning Snapshot;
    UPROPERTY() TSubclassOf<UGameplayEffect> SnapshotDamageEffect;
    TWeakObjectPtr<AStoneGolemCharacter> Golem;
    FTimerHandle UpdateTimer;
    int32 Serial=0,Lease=0;
    double Started=0,LastWarning=0;
    FVector Center=FVector::ZeroVector;
    float Yaw=0,SnapshotDamage=0;
    TArray<FVector> LockedSurface;
    TArray<int32> LockedTriangles;
    uint8 PreviousMovementMode=0;
    bool PreviousDesiredRotation=false;
    bool bLocked=false,bMontageStarted=false,bHit=false;
};

UCLASS() class TEST_25D_API UStoneGolemHeavyHammer : public UStoneGolemAttackAbility
{ GENERATED_BODY() public: UStoneGolemHeavyHammer(); };
UCLASS() class TEST_25D_API UStoneGolemQuake : public UStoneGolemAttackAbility
{ GENERATED_BODY() public: UStoneGolemQuake(); };
UCLASS() class TEST_25D_API UStoneGolemShieldBash : public UStoneGolemAttackAbility
{ GENERATED_BODY() public: UStoneGolemShieldBash(); };

// Existing behavior-tree attack tag routes through this server-only selector.
UCLASS()
class TEST_25D_API UStoneGolemSelectAttack : public UGameplayAbility
{
    GENERATED_BODY()
public:
    UStoneGolemSelectAttack();
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation,const FGameplayEventData* Event) override;
};
