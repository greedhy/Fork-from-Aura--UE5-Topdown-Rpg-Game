#include "AbilitySystem/PrototypeExtensions/ExtensionAbility.h"
#include "AbilitySystem/PrototypeExtensions/ExtensionRuntime.h"
#include "PureMass/PureMassAbility.h"
#include "PureMass/PureMassRuntime.h"
#include "PureMass/PureMassTargetData.h"
#include "AbilitySystemComponent.h"
#include "TimerManager.h"
#include "Engine/World.h"
bool UExtensionAbility::CanActivateAbility(FGameplayAbilitySpecHandle H,const FGameplayAbilityActorInfo* I,const FGameplayTagContainer* S,const FGameplayTagContainer* T,FGameplayTagContainer* R) const
{
    const auto* N=Cast<UExtensionNode>(Prototype);
    return N && N->ValidateGraph() && Super::CanActivateAbility(H,I,S,T,R);
}
void UExtensionAbility::ApplyCost(FGameplayAbilitySpecHandle,const FGameplayAbilityActorInfo* I,FGameplayAbilityActivationInfo) const
{ if (I && I->IsNetAuthority() && Prototype) UPureMassAbility::SpendMana(I->AvatarActor.Get(),Prototype->ManaCost); }
void UExtensionAbility::ActivateAbility(FGameplayAbilitySpecHandle,const FGameplayAbilityActorInfo* I,FGameplayAbilityActivationInfo,const FGameplayEventData*)
{
    bConsumed=false; CastContext=nullptr;
    auto* N=Cast<UExtensionNode>(Prototype);
    if (!I || !N || !N->ValidateGraph()) { Abort(); return; }
    if (N->bTargetSelf) { if (I->IsNetAuthority()) Execute(GetAvatarActorFromActorInfo()->GetActorLocation(),{}); return; }
    GetWorld()->GetTimerManager().SetTimer(Timeout,this,&ThisClass::Abort,3.f,false);
    auto* Task=UPureMassTargetData::Create(this); Task->Ready.AddDynamic(this,&ThisClass::TargetReady); Task->ReadyForActivation();
}
void UExtensionAbility::TargetReady(const FGameplayAbilityTargetDataHandle& Data)
{
    if (!IsActive() || bConsumed || !CurrentActorInfo) return;
    if (!CurrentActorInfo->IsNetAuthority()) { bConsumed=true; GetWorld()->GetTimerManager().ClearTimer(Timeout); return; }
    const FHitResult* Hit=Data.Num()==1 && Data.Get(0)?Data.Get(0)->GetHitResult():nullptr;
    if (!Hit || !Hit->bBlockingHit || (Hit->GetActor() && Hit->Item!=INDEX_NONE)) { Abort(); return; }
    auto T=Hit->GetActor()?FPureMassCombatTarget::FromActor(Hit->GetActor()):FPureMassCombatTarget(Hit->Item);
    FVector P; auto* N=Cast<UExtensionNode>(Prototype);
    if (!UPureMassAbility::ValidateCombatTarget(GetAvatarActorFromActorInfo(),N,T,Hit->ImpactPoint,P)
        || ((N->Behavior==EExtensionKind::Attach || N->Behavior==EExtensionKind::Chain) && !T.IsSet())) { Abort(); return; }
    Execute(P,T);
}
void UExtensionAbility::Execute(FVector P,FPureMassCombatTarget T)
{
    if (bConsumed || !IsActive() || !CurrentActorInfo->IsNetAuthority()) return;
    bConsumed=true; GetWorld()->GetTimerManager().ClearTimer(Timeout);
    auto* N=CastChecked<UExtensionNode>(Prototype); auto* Avatar=GetAvatarActorFromActorInfo();
    SetOffensiveAttackTarget(T.Actor.Get());
    if (!CanActivateAbility(CurrentSpecHandle,CurrentActorInfo) || !CommitAbility(CurrentSpecHandle,CurrentActorInfo,CurrentActivationInfo)) { Abort(); return; }
    CastContext=NewObject<UExtensionCastContext>(Avatar); CastContext->Caster=Avatar; CastContext->CastId=FGuid::NewGuid();
    CastContext->Level=GetAbilityLevel(); CastContext->DamageParams=MakeDamageEffectParamsFromClassDefaults();
    FVector Origin=P,Direction=(P-Avatar->GetActorLocation()).GetSafeNormal(SMALL_NUMBER,Avatar->GetActorForwardVector());
    if (N->Behavior==EExtensionKind::Projectile)
    {
        Origin=Avatar->GetActorLocation()+FVector(0,0,30);
        Direction=(P+(!T.IsSet()?FVector(0,0,30):FVector::ZeroVector)-Origin).GetSafeNormal(SMALL_NUMBER,Direction);
    }
    if (N->Behavior==EExtensionKind::Chain) Origin=Avatar->GetActorLocation();
    if (!AExtensionRuntime::Spawn(CastContext,N,Origin,Direction,T,0,Origin)) { Abort(); return; }
    APureMassRuntime::NotifyCommittedAttack(Avatar,this,T);
    EndAbility(CurrentSpecHandle,CurrentActorInfo,CurrentActivationInfo,true,false);
}
void UExtensionAbility::Abort() { if (IsActive()) EndAbility(CurrentSpecHandle,CurrentActorInfo,CurrentActivationInfo,true,true); }
void UExtensionAbility::EndAbility(FGameplayAbilitySpecHandle H,const FGameplayAbilityActorInfo* I,FGameplayAbilityActivationInfo A,bool Rep,bool Cancel)
{
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(Timeout);
    if (Cancel && CastContext) CastContext->bCancelled=true;
    CastContext=nullptr; Super::EndAbility(H,I,A,Rep,Cancel);
}
FString UExtensionAbility::GetDescription(int32 Level)
{
    if (!Prototype) return TEXT("");
    return FString::Printf(TEXT("<Title>%s</>\n<Default>Lv.%d | MP %.0f | CD %.1fs</>\n<Default>%s</>"),
        *Prototype->DisplayName.ToString(),Level,Prototype->ManaCost,Prototype->Cooldown,*Prototype->Summary.ToString());
}
