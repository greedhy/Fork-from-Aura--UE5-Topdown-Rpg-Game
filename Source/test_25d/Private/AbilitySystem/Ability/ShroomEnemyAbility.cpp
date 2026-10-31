#include "AbilitySystem/Ability/ShroomEnemyAbility.h"
#include "Character/TelegraphedEnemyCharacter.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "NativeGameplayTags.h"
#include "Engine/World.h"

UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShroomSlam,"Abilities.Shroom.Slam");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShroomSpore,"Abilities.Shroom.Spore");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShroomSlamCD,"Cooldown.Shroom.Slam");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_ShroomSporeCD,"Cooldown.Shroom.Spore");
UShroomSlamAbility::UShroomSlamAbility(){SetAssetTags(FGameplayTagContainer(TAG_ShroomSlam));CooldownIdentity=TAG_ShroomSlamCD;}
UShroomSporeAbility::UShroomSporeAbility(){SetAssetTags(FGameplayTagContainer(TAG_ShroomSpore));CooldownIdentity=TAG_ShroomSporeCD;}
bool UShroomSporeConfig::ValidateSpore(FString& Error) const
{
    if(!Tuning.Validate(Error)) return false;
    if(!FMath::IsFinite(Duration) || !FMath::IsFinite(Period) || Period<.1f || Duration<Period || Duration>10 || Duration/Period>20 || !Tuning.bDrawFootprint)
    {Error=TEXT("Spore requires a visible field, valid duration and bounded pulse count");return false;}
    return true;
}
bool UShroomSporeAbility::CanActivateAbility(FGameplayAbilitySpecHandle H,const FGameplayAbilityActorInfo* I,const FGameplayTagContainer* S,const FGameplayTagContainer* T,FGameplayTagContainer* R) const
{
    const auto* Config=Cast<UShroomSporeConfig>(AttackConfig);FString Error;
    return Config && Config->ValidateSpore(Error) && Super::CanActivateAbility(H,I,S,T,R);
}
void UShroomSporeAbility::ActivateAbility(FGameplayAbilitySpecHandle H,const FGameplayAbilityActorInfo* I,FGameplayAbilityActivationInfo A,const FGameplayEventData* E)
{
    bFieldActive=false;
    if(const auto* Config=Cast<UShroomSporeConfig>(AttackConfig)){FieldDuration=Config->Duration;FieldPeriod=Config->Period;}
    Super::ActivateAbility(H,I,A,E);
}
void UShroomSporeAbility::ResolveHit()
{
    if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease)){Abort();return;}
    bFieldActive=true;Clock.Reset(GetWorld()->GetTimeSeconds(),FieldPeriod,FieldDuration);
    Golem->ShowActiveFootprint(Serial,&Center);
    if(auto* Anim=Golem->GetMesh()->GetAnimInstance())
    {
        const int32 OwnedSerial=Serial,OwnedLease=Lease;
        auto Interrupted=[this,OwnedSerial,OwnedLease](UAnimMontage*,bool bInterrupted)
        {
            if(bInterrupted && IsActive() && Serial==OwnedSerial && Lease==OwnedLease && Golem.IsValid() && Golem->IsAttackCurrent(OwnedSerial,OwnedLease)) Abort();
        };
        FOnMontageBlendingOutStarted Blend;Blend.BindWeakLambda(this,Interrupted);Anim->Montage_SetBlendingOutDelegate(Blend,Snapshot.Montage);
        FOnMontageEnded End;End.BindWeakLambda(this,Interrupted);Anim->Montage_SetEndDelegate(End,Snapshot.Montage);
    }
    if(Clock.Consume(GetWorld()->GetTimeSeconds())){TArray<AActor*> Targets;GatherTargets(Targets);ApplyHitTargets(Targets);}
}
void UShroomSporeAbility::Advance()
{
    if(!IsActive()) return;
    if(!bFieldActive){Super::Advance();return;}
    if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease) || Golem->bIsStunned){Abort();return;}
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now>=Clock.Ends){EndAbility(CurrentSpecHandle,CurrentActorInfo,CurrentActivationInfo,true,false);return;}
    if(Clock.Consume(Now)){TArray<AActor*> Targets;GatherTargets(Targets);ApplyHitTargets(Targets);}
}
void UShroomSporeAbility::EndAbility(FGameplayAbilitySpecHandle H,const FGameplayAbilityActorInfo* I,FGameplayAbilityActivationInfo A,bool R,bool C)
{
    if(bFieldActive && Golem.IsValid()) if(auto* Anim=Golem->GetMesh()->GetAnimInstance())
    {FOnMontageBlendingOutStarted Blend;FOnMontageEnded End;Anim->Montage_SetBlendingOutDelegate(Blend,Snapshot.Montage);Anim->Montage_SetEndDelegate(End,Snapshot.Montage);}
    bFieldActive=false;Super::EndAbility(H,I,A,R,C);
}
