#pragma once
#include "CoreMinimal.h"
#include "Abilities/Tasks/AbilityTask.h"
#include "PureMassTargetData.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FPureMassTargetReady, const FGameplayAbilityTargetDataHandle&, Data);

/** Standard GAS hit payload: Item is a stable entity ID; Actor is always empty. */
UCLASS()
class TEST_25D_API UPureMassTargetData : public UAbilityTask
{
    GENERATED_BODY()
public:
    static UPureMassTargetData* Create(UGameplayAbility* OwningAbility);
    UPROPERTY(BlueprintAssignable) FPureMassTargetReady Ready;
    virtual void Activate() override;
    virtual void OnDestroy(bool bAbilityEnded) override;
private:
    FDelegateHandle DataDelegate;
    void Receive(const FGameplayAbilityTargetDataHandle& Data, FGameplayTag Tag);
};
