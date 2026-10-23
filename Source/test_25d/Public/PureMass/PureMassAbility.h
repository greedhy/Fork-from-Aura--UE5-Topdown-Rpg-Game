#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Prototypes/PrototypeAbility.h"
#include "PureMassAbility.generated.h"
class APureMassRuntime;

/** Player ASC is retained; enemies are addressed exclusively through stable Mass IDs. */
UCLASS()
class TEST_25D_API UPureMassAbility : public UPrototypeAbility
{
    GENERATED_BODY()
public:
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation, const FGameplayEventData* Event) override;
    virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation, bool bReplicate, bool bCancelled) override;
    virtual void ApplyCost(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation) const override;
    static bool SpendMana(AActor* Caster, float Amount);
    /** Validates a client request against authoritative entity state and world geometry. */
    static bool ValidateTarget(AActor* Caster, const UAbilityPrototype* Config, int32 Id, const FVector& Requested, FVector& Resolved);
private:
    UPROPERTY() TObjectPtr<APureMassRuntime> MassRuntime;
    FTimerHandle MassTargetTimeout;
    bool bTargetConsumed = false;
    UFUNCTION() void TargetReady(const FGameplayAbilityTargetDataHandle& Data);
    UFUNCTION() void Released(float HeldTime);
    UFUNCTION() void RuntimeDestroyed(AActor* Actor);
    void AbortMass();
    void ExecuteMass(const FVector& Point, int32 Id);
};

/** Native definition remains network-addressable; each application carries its own cost magnitude. */
UCLASS()
class TEST_25D_API UPureMassManaEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UPureMassManaEffect();
    static FGameplayTag GetManaTag();
};
