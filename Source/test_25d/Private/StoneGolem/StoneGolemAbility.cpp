#include "StoneGolem/StoneGolemAbility.h"
#include "StoneGolem/StoneGolemCharacter.h"
#include "NativeGameplayTags.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystem/MyAbilitySystemLibrary.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "AIController.h"
#include "TimerManager.h"
#include "MyGameplayTags.h"
#include "Roguelike/DungeonRunDirector.h"

UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_SGSelect,"Abilities.Attack.StoneGolem");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_SGHammer,"Abilities.StoneGolem.HeavyHammer");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_SGQuake,"Abilities.StoneGolem.Quake");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_SGShield,"Abilities.StoneGolem.ShieldBash");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_SGHammerCD,"Cooldown.StoneGolem.HeavyHammer");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_SGQuakeCD,"Cooldown.StoneGolem.Quake");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_SGShieldCD,"Cooldown.StoneGolem.ShieldBash");

UStoneGolemCooldownEffect::UStoneGolemCooldownEffect(){DurationPolicy=EGameplayEffectDurationType::HasDuration;DurationMagnitude=FScalableFloat(1.f);}
UStoneGolemAttackAbility::UStoneGolemAttackAbility()
{
    InstancingPolicy=EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy=EGameplayAbilityNetExecutionPolicy::ServerOnly;
    DebuffChance=0;KnockbackChance=0;DeathImpulseMagnitude=0;KnockbackForceMagnitude=0;
    bIsRadialDamage=false;
}
UStoneGolemHeavyHammer::UStoneGolemHeavyHammer(){SetAssetTags(FGameplayTagContainer(TAG_SGHammer));CooldownIdentity=TAG_SGHammerCD;}
UStoneGolemQuake::UStoneGolemQuake(){SetAssetTags(FGameplayTagContainer(TAG_SGQuake));CooldownIdentity=TAG_SGQuakeCD;}
UStoneGolemShieldBash::UStoneGolemShieldBash(){SetAssetTags(FGameplayTagContainer(TAG_SGShield));CooldownIdentity=TAG_SGShieldCD;}
bool UStoneGolemAttackAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    const FGameplayTagContainer* Source,const FGameplayTagContainer* Target,FGameplayTagContainer* Relevant) const
{
    auto* Actor=Info?Cast<AStoneGolemCharacter>(Info->AvatarActor.Get()):nullptr;
    FString Error;
    if(!Actor || !Info->AbilitySystemComponent.IsValid() || !AttackConfig || !AttackConfig->Tuning.Validate(Error) ||
        !Actor->MonsterConfig || !Actor->MonsterConfig->DamageEffect || !FMath::IsFinite(Actor->MonsterConfig->BaseDamage) || Actor->MonsterConfig->BaseDamage<0 ||
        Actor->IsDead_Implementation() || Actor->IsDungeonPoolSleeping() || Actor->IsAttacking() || Actor->bIsStunned ||
        !Actor->GetMesh()->GetAnimInstance() || !Actor->GetMesh()->GetSkeletalMeshAsset() || Actor->GetMesh()->GetSkeletalMeshAsset()->GetSkeleton()!=AttackConfig->Tuning.Montage->GetSkeleton()) return false;
    AActor* Victim=Actor->CombatTarget;
    if(!IsValid(Victim) || !Victim->Implements<UCombatInterface>() || ICombatInterface::Execute_IsDead(Victim) ||
        !UMyAbilitySystemLibrary::IsNotFriend(Actor,Victim) || !ADungeonRunDirector::AllowsCombat(Actor,Victim) ||
        Actor->GetDistanceTo(Victim)>AttackConfig->Tuning.ActivationRange) return false;
    return Super::CanActivateAbility(Handle,Info,Source,Target,Relevant);
}
bool UStoneGolemAttackAbility::CheckCooldown(FGameplayAbilitySpecHandle,const FGameplayAbilityActorInfo* Info,FGameplayTagContainer*) const
{
    return Info && Info->AbilitySystemComponent.IsValid() && CooldownIdentity.IsValid() && !Info->AbilitySystemComponent->HasMatchingGameplayTag(CooldownIdentity);
}
void UStoneGolemAttackAbility::ApplyCooldown(FGameplayAbilitySpecHandle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo) const
{
    if(!Info || !Info->IsNetAuthority()) return;
    auto* ASC=Info->AbilitySystemComponent.Get();
    auto Spec=ASC->MakeOutgoingSpec(UStoneGolemCooldownEffect::StaticClass(),1,ASC->MakeEffectContext());
    if(Spec.IsValid()) {Spec.Data->SetDuration(Snapshot.Cooldown,true);Spec.Data->DynamicGrantedTags.AddTag(CooldownIdentity);ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());}
}
void UStoneGolemAttackAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation,const FGameplayEventData*)
{
    Serial=0;bHit=false;bLocked=false;bMontageStarted=false;LockedSurface.Reset();LockedTriangles.Reset();
    if(!Info || !Info->IsNetAuthority() || !CanActivateAbility(Handle,Info)){Abort();return;}
    Golem=Cast<AStoneGolemCharacter>(Info->AvatarActor.Get());
    Snapshot=AttackConfig->Tuning;SnapshotDamage=Golem->MonsterConfig->BaseDamage*Snapshot.DamageMultiplier;
    SnapshotDamageEffect=Golem->MonsterConfig->DamageEffect;
    Lease=Golem->GetDungeonPoolLease();Started=GetWorld()->GetTimeSeconds();LastWarning=Started;
    if(!UpdateAim() || !CommitAbility(Handle,Info,Activation)){Abort();return;}
    Serial=Golem->BeginAttack(Snapshot,Center,Yaw);
    if(!Serial){Abort();return;}
    auto* Movement=Golem->GetCharacterMovement();
    PreviousMovementMode=Movement->MovementMode;PreviousDesiredRotation=Movement->bUseControllerDesiredRotation;
    Movement->StopMovementImmediately();Movement->DisableMovement();Movement->bUseControllerDesiredRotation=false;
    if(auto* AI=Cast<AAIController>(Golem->GetController())){AI->StopMovement();AI->ClearFocus(EAIFocusPriority::Gameplay);}
    bLocked=Snapshot.LockTime<=0;
    if(bLocked) StoneGolemGeometry::BuildSurface(GetWorld(),Golem.Get(),Snapshot,Center,Yaw,LockedSurface,LockedTriangles);
    GetWorld()->GetTimerManager().SetTimer(UpdateTimer,this,&ThisClass::Advance,.01f,true);
    Advance();
}
bool UStoneGolemAttackAbility::UpdateAim()
{
    if(!Golem.IsValid()) return false;
    if(IsValid(Golem->CombatTarget))
    {
        const FVector Direction=Golem->CombatTarget->GetActorLocation()-Golem->GetActorLocation();
        if(!Direction.IsNearlyZero()) Yaw=Direction.Rotation().Yaw;
    }
    FVector Origin=Golem->GetActorLocation()-FVector(0,0,Golem->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Candidate=Origin+FRotator(0,Yaw,0).RotateVector(Snapshot.CenterOffset);
    if(!StoneGolemGeometry::Project(GetWorld(),Golem.Get(),Candidate,Snapshot.HeightTolerance,Center)) return false;
    Golem->SetActorRotation(FRotator(0,Yaw,0));return true;
}
void UStoneGolemAttackAbility::Advance()
{
    if(!IsActive()) return;
    if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease) || Golem->bIsStunned){Abort();return;}
    const double Now=GetWorld()->GetTimeSeconds();const float Elapsed=Now-Started;
    if(!bLocked)
    {
        if(!UpdateAim()){Abort();return;}
        if(Elapsed>=Snapshot.LockTime || Now-LastWarning>=.1)
        {Golem->UpdateWarning(Serial,Center,Yaw);LastWarning=Now;}
        bLocked=Elapsed>=Snapshot.LockTime;
        if(bLocked) StoneGolemGeometry::BuildSurface(GetWorld(),Golem.Get(),Snapshot,Center,Yaw,LockedSurface,LockedTriangles);
    }
    if(!bMontageStarted && Elapsed>=Snapshot.AnimationDelay)
    {
        bMontageStarted=true;
        if(CurrentActorInfo->AbilitySystemComponent->PlayMontage(this,CurrentActivationInfo,Snapshot.Montage,Snapshot.PlayRate)<=0){Abort();return;}
    }
    if(bMontageStarted && !bHit)
    {
        auto* Anim=Golem->GetMesh()->GetAnimInstance();
        if(!Anim || !Anim->Montage_IsActive(Snapshot.Montage)){Abort();return;}
        const float Position=Anim->Montage_GetPosition(Snapshot.Montage);
        if(Position>=Snapshot.ContactTime)
        {
            // The montage is the only hit clock; missed windows do not generate delayed damage.
            if(Position>Snapshot.ContactTime+Snapshot.ContactTolerance){Abort();return;}
            bHit=true;ResolveHit();
            if(!IsActive()) return;
        }
    }
    if(Elapsed>Snapshot.RecoveryEnd+.25f || (Elapsed>=Snapshot.RecoveryEnd && bHit))
        EndAbility(CurrentSpecHandle,CurrentActorInfo,CurrentActivationInfo,true,!bHit);
}
void UStoneGolemAttackAbility::GatherTargets(TArray<AActor*>& Out) const
{
    Out.Reset();if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease)) return;
    TArray<AActor*> Candidates;
    UMyAbilitySystemLibrary::GetLivePlayersWithinRadius(Golem.Get(),Candidates,{Golem.Get()},Snapshot.Radius+200,Center);
    for(auto* Target:Candidates)
    {
        if(!IsValid(Target) || !Target->Implements<UCombatInterface>() || ICombatInterface::Execute_IsDead(Target) ||
            !UMyAbilitySystemLibrary::IsNotFriend(Golem.Get(),Target) || !ADungeonRunDirector::AllowsCombat(Golem.Get(),Target) ||
            !UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Target)) continue;
        FVector Feet=Target->GetActorLocation();
        if(const auto* Character=Cast<ACharacter>(Target)) Feet.Z-=Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        FVector Ground;
        if(!Snapshot.Contains(Center,Yaw,Feet) || !StoneGolemGeometry::SurfaceContains(LockedSurface,LockedTriangles,Feet) || !StoneGolemGeometry::Project(GetWorld(),Golem.Get(),FVector(Feet.X,Feet.Y,Center.Z),Snapshot.HeightTolerance,Ground) ||
            FMath::Abs(Feet.Z-Ground.Z)>Snapshot.HeightTolerance || !StoneGolemGeometry::Visible(GetWorld(),Golem.Get(),Center,Ground)) continue;
        Out.AddUnique(Target);
    }
}
void UStoneGolemAttackAbility::ResolveHit()
{
    if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease)) return;
    FVector Impact=Center;
    const FVector Weapon=Golem->GetMesh()->GetSocketLocation(Snapshot.ImpactSocket);
    FVector Projected;
    if(StoneGolemGeometry::Project(GetWorld(),Golem.Get(),FVector(Weapon.X,Weapon.Y,Center.Z),Snapshot.HeightTolerance,Projected)) Impact=Projected;
    Golem->ShowImpact(Serial,Impact);
    TArray<AActor*> Targets;GatherTargets(Targets);
    if(!Targets.IsEmpty()) ReportOffensiveAttack(Targets[0]);
    for(auto* Target:Targets)
    {
        if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease)) break;
        if(!IsValid(Target) || ICombatInterface::Execute_IsDead(Target)) continue;
        auto Params=MakeDamageEffectParamsFromClassDefaults(Target);
        Params.DamageGameplayEffectClass=SnapshotDamageEffect;
        Params.DamageType=FMyGameplayTags::Get().Damage_Physics;
        Params.BaseDamage=SnapshotDamage;Params.DebuffChance=0;Params.bIsRadialDamage=false;
        Params.KnockbackChance=Snapshot.KnockbackSpeed>0?100:0;
        Params.KnockbackForce=(Target->GetActorLocation()-Golem->GetActorLocation()).GetSafeNormal2D()*Snapshot.KnockbackSpeed;
        UMyAbilitySystemLibrary::ApplyDamageEffect(Params);
    }
}
void UStoneGolemAttackAbility::Abort(){EndAbility(CurrentSpecHandle,CurrentActorInfo,CurrentActivationInfo,true,true);}
void UStoneGolemAttackAbility::EndAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation,bool Replicate,bool Cancelled)
{
    if(GetWorld()) GetWorld()->GetTimerManager().ClearTimer(UpdateTimer);
    if(Serial && Golem.IsValid())
    {
        if(Info && Info->AbilitySystemComponent.IsValid() && Info->AbilitySystemComponent->GetAnimatingAbility()==this)
            Info->AbilitySystemComponent->CurrentMontageStop(.15f);
        Golem->FinishAttack(Serial);
        if(!Golem->IsAttacking() && !Golem->IsDead_Implementation() && !Golem->IsDungeonPoolSleeping() && Golem->GetDungeonPoolLease()==Lease)
        {
            Golem->GetCharacterMovement()->SetMovementMode(EMovementMode(PreviousMovementMode));
            Golem->GetCharacterMovement()->bUseControllerDesiredRotation=PreviousDesiredRotation;
            Golem->RefreshMovementSpeed();
        }
    }
    Serial=0;Golem.Reset();Super::EndAbility(Handle,Info,Activation,Replicate,Cancelled);
}
UStoneGolemSelectAttack::UStoneGolemSelectAttack()
{
    InstancingPolicy=EGameplayAbilityInstancingPolicy::InstancedPerActor;NetExecutionPolicy=EGameplayAbilityNetExecutionPolicy::ServerOnly;
    SetAssetTags(FGameplayTagContainer(TAG_SGSelect));
}
void UStoneGolemSelectAttack::ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation,const FGameplayEventData*)
{
    if(Info && Info->IsNetAuthority()) if(auto* Actor=Cast<AStoneGolemCharacter>(Info->AvatarActor.Get())) Actor->TryChooseAttack();
    EndAbility(Handle,Info,Activation,true,false);
}
