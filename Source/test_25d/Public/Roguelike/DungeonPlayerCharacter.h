#pragma once
#include "CoreMinimal.h"
#include "PureMass/PureMassPlayerCharacter.h"
#include "DungeonPlayerCharacter.generated.h"

/** Run-owned death lifecycle retains the same pawn, ASC and backpack. */
UCLASS()
class TEST_25D_API ADungeonPlayerCharacter : public APureMassPlayerCharacter
{
    GENERATED_BODY()
public:
    virtual void Die(const FVector& DeathImpulse) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(ReplicatedUsing=OnRep_Downed, BlueprintReadOnly) bool bDungeonDowned = false;
    UFUNCTION(BlueprintCallable) bool ReviveForDungeon(FVector SafeLocation, float Fraction = .3f);
    UFUNCTION(BlueprintPure) bool IsDungeonDowned() const { return bDungeonDowned; }
protected:
    virtual void InitAbilityActorInfo() override;
private:
    UFUNCTION() void OnRep_Downed();
    void UpdateDownedInputBlock();
    TWeakObjectPtr<UAbilitySystemComponent> DownedInputASC;
    TArray<FGameplayAbilitySpecHandle> PausedPassiveAbilities;
    bool bAppliedDowned = false;
    ECollisionEnabled::Type LivingCapsuleCollision = ECollisionEnabled::QueryAndPhysics;
};
