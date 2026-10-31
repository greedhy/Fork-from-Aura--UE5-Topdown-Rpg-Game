#include "AbilitySystem/Ability/TelegraphedEnemyAbility.h"
#include "Character/TelegraphedEnemyCharacter.h"
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

UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_SGSelect,"Abilities.Attack.ConfiguredMonster");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_DemonClaw,"Abilities.Demon.Claw");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_DemonTail,"Abilities.Demon.Tailspin");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_DemonClawCD,"Cooldown.Demon.Claw");
UE_DEFINE_GAMEPLAY_TAG_STATIC(TAG_DemonTailCD,"Cooldown.Demon.Tailspin");
UDemonClawAbility::UDemonClawAbility(){SetAssetTags(FGameplayTagContainer(TAG_DemonClaw));CooldownIdentity=TAG_DemonClawCD;}
UDemonTailspinAbility::UDemonTailspinAbility(){SetAssetTags(FGameplayTagContainer(TAG_DemonTail));CooldownIdentity=TAG_DemonTailCD;}

UStoneGolemCooldownEffect::UStoneGolemCooldownEffect(){DurationPolicy=EGameplayEffectDurationType::HasDuration;DurationMagnitude=FScalableFloat(1.f);}
UTelegraphedEnemyAbility::UTelegraphedEnemyAbility()
{
    InstancingPolicy=EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy=EGameplayAbilityNetExecutionPolicy::ServerOnly;
    DebuffChance=0;KnockbackChance=0;DeathImpulseMagnitude=0;KnockbackForceMagnitude=0;
    bIsRadialDamage=false;
}
bool UTelegraphedEnemyAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    const FGameplayTagContainer* Source,const FGameplayTagContainer* Target,FGameplayTagContainer* Relevant) const
{
    auto* Actor=Info?Cast<ATelegraphedEnemyCharacter>(Info->AvatarActor.Get()):nullptr;
    FString Error;
    if(!Actor || !Info->AbilitySystemComponent.IsValid() || !AttackConfig || !AttackConfig->Tuning.Validate(Error) ||
        !Actor->GetCombatConfig() || !Actor->GetCombatConfig()->DamageEffect || !FMath::IsFinite(Actor->GetCombatConfig()->BaseDamage) || Actor->GetCombatConfig()->BaseDamage<0 ||
        Actor->IsDead_Implementation() || Actor->IsDungeonPoolSleeping() || Actor->IsAttacking() || Actor->bIsStunned ||
        !Actor->GetMesh()->GetAnimInstance() || !Actor->GetMesh()->GetSkeletalMeshAsset() || Actor->GetMesh()->GetSkeletalMeshAsset()->GetSkeleton()!=AttackConfig->Tuning.Montage->GetSkeleton()) return false;
    AActor* Victim=Actor->CombatTarget;
    if(!IsValid(Victim) || !Victim->Implements<UCombatInterface>() || ICombatInterface::Execute_IsDead(Victim) ||
        !UMyAbilitySystemLibrary::IsNotFriend(Actor,Victim) || !ADungeonRunDirector::AllowsCombat(Actor,Victim) ||
        Actor->GetDistanceTo(Victim)>AttackConfig->Tuning.ActivationRange) return false;
    if(AttackConfig->Tuning.bRequireLineOfSight && !StoneGolemGeometry::Visible(Actor->GetWorld(),Actor,
        Actor->GetActorLocation(),Victim->GetActorLocation())) return false;
    return Super::CanActivateAbility(Handle,Info,Source,Target,Relevant);
}
bool UTelegraphedEnemyAbility::CheckCooldown(FGameplayAbilitySpecHandle,const FGameplayAbilityActorInfo* Info,FGameplayTagContainer*) const
{
    return Info && Info->AbilitySystemComponent.IsValid() && CooldownIdentity.IsValid() && !Info->AbilitySystemComponent->HasMatchingGameplayTag(CooldownIdentity);
}
void UTelegraphedEnemyAbility::ApplyCooldown(FGameplayAbilitySpecHandle,const FGameplayAbilityActorInfo* Info,FGameplayAbilityActivationInfo) const
{
    if(!Info || !Info->IsNetAuthority()) return;
    auto* ASC=Info->AbilitySystemComponent.Get();
    auto Spec=ASC->MakeOutgoingSpec(UStoneGolemCooldownEffect::StaticClass(),1,ASC->MakeEffectContext());
    if(Spec.IsValid()) {Spec.Data->SetDuration(Snapshot.Cooldown,true);Spec.Data->DynamicGrantedTags.AddTag(CooldownIdentity);ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());}
}
void UTelegraphedEnemyAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation,const FGameplayEventData*)
{
    Serial=0;bHit=false;bLocked=false;bMontageStarted=false;LockedSurface.Reset();LockedTriangles.Reset();
    if(!Info || !Info->IsNetAuthority() || !CanActivateAbility(Handle,Info)){Abort();return;}
    Golem=Cast<ATelegraphedEnemyCharacter>(Info->AvatarActor.Get());
    Snapshot=AttackConfig->Tuning;SnapshotDamage=Golem->GetCombatConfig()->BaseDamage*Snapshot.DamageMultiplier;
    SelectedTarget=Golem->CombatTarget;
    SnapshotDamageEffect=Golem->GetCombatConfig()->DamageEffect;
    SnapshotDamageType=AttackConfig->DamageType.IsValid()?AttackConfig->DamageType:FMyGameplayTags::Get().Damage_Physics;
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
bool UTelegraphedEnemyAbility::UpdateAim()
{
    if(!Golem.IsValid()) return false;
    if(IsValid(Golem->CombatTarget))
    {
        const FVector Direction=Golem->CombatTarget->GetActorLocation()-Golem->GetActorLocation();
        if(!Direction.IsNearlyZero()) Yaw=Direction.Rotation().Yaw;
    }
    FVector Origin=Golem->GetActorLocation()-FVector(0,0,Golem->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    if(Snapshot.bTargetGround)
    {
        if(!SelectedTarget.IsValid()) return false;
        Origin=SelectedTarget->GetActorLocation();
        if(const auto* Character=Cast<ACharacter>(SelectedTarget.Get())) Origin.Z-=Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    }
    const FVector Candidate=Origin+FRotator(0,Yaw,0).RotateVector(Snapshot.CenterOffset);
    if(!StoneGolemGeometry::Project(GetWorld(),Golem.Get(),Candidate,Snapshot.HeightTolerance,Center)) return false;
    Golem->SetActorRotation(FRotator(0,Yaw,0));return true;
}
void UTelegraphedEnemyAbility::Advance()
{
    if(!IsActive()) return;
    if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease) || Golem->bIsStunned){Abort();return;}
    const double Now=GetWorld()->GetTimeSeconds();const float Elapsed=Now-Started;
    if(!bLocked)
    {
        if(!UpdateAim()){Abort();return;}
        if(Elapsed>=Snapshot.LockTime || Now-LastWarning>=.1)
        {Golem->UpdateWarning(Serial,Center,Yaw,&Snapshot);LastWarning=Now;}
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
void UTelegraphedEnemyAbility::GatherTargets(TArray<AActor*>& Out) const
{
    Out.Reset();if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease)) return;
    TArray<AActor*> Candidates;
    UMyAbilitySystemLibrary::GetLivePlayersWithinRadius(Golem.Get(),Candidates,{Golem.Get()},Snapshot.QueryRadius()+200,Center);
    for(auto* Target:Candidates)
    {
        if(Snapshot.bSingleTarget && Target!=SelectedTarget.Get()) continue;
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
void UTelegraphedEnemyAbility::ResolveHit()
{
    if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease)) return;
    FVector Impact=Center;
    const FVector Weapon=Snapshot.bTargetGround?Center:
        Snapshot.bImpactAtTarget && SelectedTarget.IsValid()?SelectedTarget->GetActorLocation():Golem->GetMesh()->GetSocketLocation(Snapshot.ImpactSocket);
    FVector Projected;
    if(StoneGolemGeometry::Project(GetWorld(),Golem.Get(),FVector(Weapon.X,Weapon.Y,Center.Z),Snapshot.HeightTolerance,Projected)) Impact=Projected;
    Golem->ShowImpact(Serial,Impact);
    TArray<AActor*> Targets;GatherTargets(Targets);
    ApplyHitTargets(Targets);
}
void UTelegraphedEnemyAbility::ApplyHitTargets(const TArray<AActor*>& Targets)
{
    if(!Targets.IsEmpty()) ReportOffensiveAttack(Targets[0]);
    for(auto* Target:Targets)
    {
        if(!Golem.IsValid() || !Golem->IsAttackCurrent(Serial,Lease)) break;
        if(!IsValid(Target) || ICombatInterface::Execute_IsDead(Target)) continue;
        auto Params=MakeDamageEffectParamsFromClassDefaults(Target);
        Params.DamageGameplayEffectClass=SnapshotDamageEffect;
        Params.DamageType=SnapshotDamageType;
        Params.BaseDamage=SnapshotDamage;Params.DebuffChance=0;Params.bIsRadialDamage=false;
        Params.KnockbackChance=Snapshot.KnockbackSpeed>0 || Snapshot.KnockbackUpSpeed>0?100:0;
        Params.KnockbackForce=(Target->GetActorLocation()-Golem->GetActorLocation()).GetSafeNormal2D()*Snapshot.KnockbackSpeed;
        Params.KnockbackForce.Z=Snapshot.KnockbackUpSpeed;
        UMyAbilitySystemLibrary::ApplyDamageEffect(Params);
    }
}
void UTelegraphedEnemyAbility::Abort(){EndAbility(CurrentSpecHandle,CurrentActorInfo,CurrentActivationInfo,true,true);}
void UTelegraphedEnemyAbility::EndAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
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
    Serial=0;Golem.Reset();SelectedTarget.Reset();Super::EndAbility(Handle,Info,Activation,Replicate,Cancelled);
}
UTelegraphedSelectAttack::UTelegraphedSelectAttack()
{
    InstancingPolicy=EGameplayAbilityInstancingPolicy::InstancedPerActor;NetExecutionPolicy=EGameplayAbilityNetExecutionPolicy::ServerOnly;
    SetAssetTags(FGameplayTagContainer(TAG_SGSelect));
}
void UTelegraphedSelectAttack::ActivateAbility(FGameplayAbilitySpecHandle Handle,const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation,const FGameplayEventData*)
{
    if(Info && Info->IsNetAuthority()) if(auto* Actor=Cast<ATelegraphedEnemyCharacter>(Info->AvatarActor.Get())) Actor->TryChooseAttack();
    EndAbility(Handle,Info,Activation,true,false);
}
