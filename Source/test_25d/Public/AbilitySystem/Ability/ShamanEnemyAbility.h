#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Ability/TelegraphedEnemyAbility.h"
#include "ShamanEnemyAbility.generated.h"
class UShamanSummonConfig;

UCLASS()
class TEST_25D_API UShamanCastAbility : public UTelegraphedEnemyAbility
{ GENERATED_BODY() public: UShamanCastAbility(); };
UCLASS()
class TEST_25D_API UShamanBurstAbility : public UTelegraphedEnemyAbility
{ GENERATED_BODY() public: UShamanBurstAbility(); };
UCLASS()
class TEST_25D_API UShamanSummonAbility : public UTelegraphedEnemyAbility
{
    GENERATED_BODY()
public:
    UShamanSummonAbility();
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        FGameplayAbilityActivationInfo Activation,const FGameplayEventData* Event) override;
    virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        const FGameplayTagContainer* Source=nullptr,const FGameplayTagContainer* Target=nullptr,FGameplayTagContainer* Relevant=nullptr) const override;
protected:
    virtual void ResolveHit() override;
    UPROPERTY(Transient) TObjectPtr<UShamanSummonConfig> SummonSnapshot;
};
