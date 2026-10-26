#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Prototypes/PrototypeAbility.h"
#include "PureMass/PureMassCombatTarget.h"
#include "ExtensionAbility.generated.h"
UCLASS()
class TEST_25D_API UExtensionAbility : public UPrototypeAbility
{
    GENERATED_BODY()
public:
    virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        const FGameplayTagContainer* Source=nullptr,const FGameplayTagContainer* Target=nullptr,FGameplayTagContainer* Relevant=nullptr) const override;
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo Activation,const FGameplayEventData* Event) override;
    virtual void EndAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo Activation,bool bReplicate,bool bCancelled) override;
    virtual void ApplyCost(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo Activation) const override;
    virtual FString GetDescription(int32 Level) override;
    virtual FString GetNextLevelDescription(int32 Level) override { return GetDescription(Level); }
private:
    bool bConsumed=false;
    FTimerHandle Timeout;
    UPROPERTY() TObjectPtr<class UExtensionCastContext> CastContext;
    UFUNCTION() void TargetReady(const FGameplayAbilityTargetDataHandle& Data);
    void Execute(FVector Position,FPureMassCombatTarget Target);
    void Abort();
};
