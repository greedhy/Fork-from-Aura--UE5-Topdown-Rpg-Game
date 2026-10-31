#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Ability/TelegraphedEnemyAbility.h"
#include "GruxEnemyAbility.generated.h"

UENUM(BlueprintType)
enum class EGruxAttackKind : uint8 { Combo, Charge, Roar };

UCLASS(BlueprintType)
class TEST_25D_API UGruxAttackConfig : public UStoneGolemAttackConfig
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Grux") EGruxAttackKind Kind=EGruxAttackKind::Combo;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Grux") FStoneGolemAttackTuning Followup;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Grux") float ChargeDuration=.5f;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Grux") float RoarArmor=25;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Grux") float RoarDuration=6;
    bool ValidateGrux(FString& Error) const;
};

UCLASS(Abstract)
class TEST_25D_API UGruxEnemyAbility : public UTelegraphedEnemyAbility
{
    GENERATED_BODY()
public:
    virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        const FGameplayTagContainer* Source=nullptr,const FGameplayTagContainer* Target=nullptr,FGameplayTagContainer* Relevant=nullptr) const override;
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo Activation,const FGameplayEventData* Event) override;
    virtual void EndAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo Activation,bool Replicate,bool Cancelled) override;
protected:
    EGruxAttackKind Kind=EGruxAttackKind::Combo;
    virtual bool UpdateAim() override;
    virtual void Advance() override;
    virtual void ResolveHit() override;
private:
    bool BeginFollowup();
    void AdvanceCharge();
    void ObserveMontage();
    void ClearMontageDelegates();
    TWeakObjectPtr<UAnimMontage> ObservedMontage;
    UPROPERTY() TObjectPtr<UGruxAttackConfig> FrozenConfig;
    int32 Stage=0,ChargeRoom=INDEX_NONE;
    float BaseDamageSnapshot=0;
    double ChargeStarted=0;
    bool bCharging=false;
    FVector ChargeStart=FVector::ZeroVector,PreviousChargePosition=FVector::ZeroVector;
    TSet<TWeakObjectPtr<AActor>> ChargedTargets;
    FActiveGameplayEffectHandle AppliedArmor;
};
UCLASS()
class TEST_25D_API UGruxComboAbility : public UGruxEnemyAbility
{GENERATED_BODY() public: UGruxComboAbility();};
UCLASS()
class TEST_25D_API UGruxChargeAbility : public UGruxEnemyAbility
{GENERATED_BODY() public: UGruxChargeAbility();};
UCLASS()
class TEST_25D_API UGruxRoarAbility : public UGruxEnemyAbility
{GENERATED_BODY() public: UGruxRoarAbility();};
