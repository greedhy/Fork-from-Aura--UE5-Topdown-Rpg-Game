#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Ability/MyDamageGameplayAbility.h"
#include "GameplayEffect.h"
#include "StoneGolem/StoneGolemConfig.h"
#include "TelegraphedEnemyAbility.generated.h"
class ATelegraphedEnemyCharacter;

UCLASS()
class TEST_25D_API UStoneGolemCooldownEffect : public UGameplayEffect
{
    GENERATED_BODY()
public: UStoneGolemCooldownEffect();
};

UCLASS()
class TEST_25D_API UTelegraphedEnemyAbility : public UMyDamageGameplayAbility
{
    GENERATED_BODY()
public:
    UTelegraphedEnemyAbility();
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
    UPROPERTY(EditDefaultsOnly, Category="Combat") FGameplayTag CooldownIdentity;
protected:
    virtual void Advance();
    void Abort();
    virtual bool UpdateAim();
    virtual void ResolveHit();
    void ApplyHitTargets(const TArray<AActor*>& Targets);
    UPROPERTY() FStoneGolemAttackTuning Snapshot;
    UPROPERTY() TSubclassOf<UGameplayEffect> SnapshotDamageEffect;
    FGameplayTag SnapshotDamageType;
    TWeakObjectPtr<ATelegraphedEnemyCharacter> Golem;
    TWeakObjectPtr<AActor> SelectedTarget;
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

UCLASS()
class TEST_25D_API UDemonClawAbility : public UTelegraphedEnemyAbility
{ GENERATED_BODY() public: UDemonClawAbility(); };
UCLASS()
class TEST_25D_API UDemonTailspinAbility : public UTelegraphedEnemyAbility
{ GENERATED_BODY() public: UDemonTailspinAbility(); };

// Existing behavior-tree attack tag routes through this server-only selector.
UCLASS()
class TEST_25D_API UTelegraphedSelectAttack : public UGameplayAbility
{
    GENERATED_BODY()
public:
    UTelegraphedSelectAttack();
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation,const FGameplayEventData* Event) override;
};
