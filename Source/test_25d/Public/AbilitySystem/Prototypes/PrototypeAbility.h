#pragma once

#include "CoreMinimal.h"
#include "AbilitySystem/Ability/MyDamageGameplayAbility.h"
#include "GameplayEffect.h"
#include "PrototypeAbility.generated.h"

class UAbilityPrototype;
class APrototypeRuntime;

UCLASS()
class TEST_25D_API UPrototypeAbility : public UMyDamageGameplayAbility
{
    GENERATED_BODY()
public:
    UPrototypeAbility();
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly) TObjectPtr<UAbilityPrototype> Prototype;
    virtual bool IsInputToggleAbility() const override;
    virtual bool ShouldCancelOnEquipChange() const override { return true; }
    virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        const FGameplayTagContainer* Source = nullptr, const FGameplayTagContainer* Target = nullptr,
        FGameplayTagContainer* Relevant = nullptr) const override;
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation, const FGameplayEventData* Event) override;
    virtual void EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation, bool bReplicate, bool bCancelled) override;
    virtual bool CheckCost(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayTagContainer* Relevant = nullptr) const override;
    virtual void ApplyCost(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation) const override;
    virtual bool CheckCooldown(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayTagContainer* Relevant = nullptr) const override;
    virtual void ApplyCooldown(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation) const override;
    virtual FString GetDescription(int32 Level) override;
    virtual FString GetNextLevelDescription(int32 Level) override;
private:
    UPROPERTY() TObjectPtr<APrototypeRuntime> Runtime;
    FTimerHandle TargetTimeout;
    bool bReceivedTarget = false;
    UFUNCTION() void OnTargetData(const FGameplayAbilityTargetDataHandle& Data);
    UFUNCTION() void OnReleased(float HeldTime);
    UFUNCTION() void OnRuntimeDestroyed(AActor* Actor);
    void Abort();
    void Execute(const FVector& Position, AActor* Target);
};

/** Stable native definition so duration effects replicate correctly. */
UCLASS()
class TEST_25D_API UPrototypeCooldownEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UPrototypeCooldownEffect();
};
