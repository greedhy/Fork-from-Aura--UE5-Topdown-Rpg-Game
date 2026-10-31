#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Ability/TelegraphedEnemyAbility.h"
#include "ShroomEnemyAbility.generated.h"

/** Server field cadence: consume at most one due pulse, never replay missed slots. */
struct FShroomPulseClock
{
    double Started=0,Ends=0;
    float Period=1;
    int32 NextSlot=0;
    void Reset(double Now,float InPeriod,float Duration){Started=Now;Ends=Now+Duration;Period=InPeriod;NextSlot=0;}
    bool Consume(double Now)
    {
        if(!FMath::IsFinite(Now) || !FMath::IsFinite(Period) || Period<=0 || Now<Started || Now>=Ends) return false;
        const int32 Slot=FMath::FloorToInt((Now-Started)/Period+1.e-6);
        if(Slot<NextSlot) return false;
        NextSlot=Slot+1;return true;
    }
};

UCLASS(BlueprintType)
class TEST_25D_API UShroomSporeConfig : public UStoneGolemAttackConfig
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Spore") float Duration=3;
    UPROPERTY(EditAnywhere,BlueprintReadOnly,Category="Spore") float Period=1;
    bool ValidateSpore(FString& Error) const;
};
UCLASS()
class TEST_25D_API UShroomSlamAbility : public UTelegraphedEnemyAbility
{GENERATED_BODY() public: UShroomSlamAbility();};

UCLASS()
class TEST_25D_API UShroomSporeAbility : public UTelegraphedEnemyAbility
{
    GENERATED_BODY()
public:
    UShroomSporeAbility();
    virtual bool CanActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
        const FGameplayTagContainer* Source=nullptr,const FGameplayTagContainer* Target=nullptr,FGameplayTagContainer* Relevant=nullptr) const override;
    virtual void ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo Activation,const FGameplayEventData* Event) override;
    virtual void EndAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo Activation,bool Replicate,bool Cancelled) override;
protected:
    virtual void ResolveHit() override;
    virtual void Advance() override;
private:
    FShroomPulseClock Clock;
    float FieldDuration=3,FieldPeriod=1;
    bool bFieldActive=false;
};
