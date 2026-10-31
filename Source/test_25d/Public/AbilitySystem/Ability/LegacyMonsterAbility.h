#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Ability/TelegraphedEnemyAbility.h"
#include "LegacyMonsterAbility.generated.h"
class AEnemySlingProjectile;
UCLASS()
class TEST_25D_API UGoblinSpearAbility : public UTelegraphedEnemyAbility
{ GENERATED_BODY() public: UGoblinSpearAbility(); };
UCLASS()
class TEST_25D_API UGhoulLeftAbility : public UTelegraphedEnemyAbility
{ GENERATED_BODY() public: UGhoulLeftAbility(); };
UCLASS()
class TEST_25D_API UGhoulRightAbility : public UTelegraphedEnemyAbility
{ GENERATED_BODY() public: UGhoulRightAbility(); };
UCLASS(BlueprintType)
class TEST_25D_API USlingAttackConfig : public UStoneGolemAttackConfig
{
 GENERATED_BODY()
public:
 UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Projectile") TSubclassOf<AEnemySlingProjectile> ProjectileClass;
 UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Projectile") float Speed=550;
 UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Projectile") float Lifetime=2;
 UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Projectile") FName MuzzleSocket=TEXT("Hand-L");
 bool ValidateProjectile() const;
};
UCLASS()
class TEST_25D_API UGoblinSlingAbility : public UTelegraphedEnemyAbility
{
 GENERATED_BODY()
public:
 UGoblinSlingAbility();
 virtual bool CanActivateAbility(FGameplayAbilitySpecHandle H,const FGameplayAbilityActorInfo* I,const FGameplayTagContainer* S=nullptr,const FGameplayTagContainer* T=nullptr,FGameplayTagContainer* R=nullptr) const override;
 virtual void EndAbility(FGameplayAbilitySpecHandle H,const FGameplayAbilityActorInfo* I,FGameplayAbilityActivationInfo A,bool R,bool C) override;
protected:
 virtual bool UpdateAim() override;
 virtual void ResolveHit() override;
private:
 FVector LockedAim=FVector::ZeroVector;
 TWeakObjectPtr<AEnemySlingProjectile> Launched;
};
