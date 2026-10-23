#include "PureMass/PureMassAbility.h"
#include "PureMass/PureMassRuntime.h"
#include "PureMass/PureMassTargetData.h"
#include "PureMass/PureMassSubsystem.h"
#include "PureMass/PureMassIncomingDamageEffect.h"
#include "AbilitySystem/Prototypes/PrototypeRuntime.h"
#include "AbilitySystem/MyAttributeSet.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "Abilities/Tasks/AbilityTask_WaitInputRelease.h"
#include "Engine/World.h"
#include "TimerManager.h"

FGameplayTag UPureMassManaEffect::GetManaTag()
{
    // Reuse the existing native-registered Damage.Physics key; it is only a magnitude key in this effect.
    return UPureMassIncomingDamageEffect::GetDamageTag();
}

UPureMassManaEffect::UPureMassManaEffect()
{
    DurationPolicy = EGameplayEffectDurationType::Instant;
    FSetByCallerFloat Amount;
    Amount.DataTag = GetManaTag();
    FGameplayModifierInfo& Modifier = Modifiers.AddDefaulted_GetRef();
    Modifier.Attribute = UMyAttributeSet::GetManaAttribute();
    Modifier.ModifierOp = EGameplayModOp::Additive;
    Modifier.ModifierMagnitude = FGameplayEffectModifierMagnitude(Amount);
}

bool UPureMassAbility::SpendMana(AActor* Caster, float Amount)
{
    if (!IsValid(Caster) || !Caster->HasAuthority() || !FMath::IsFinite(Amount) || Amount < 0.f) return false;
    auto* ASC = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Caster);
    if (!ASC || !ASC->HasAttributeSetForAttribute(UMyAttributeSet::GetManaAttribute())
        || ASC->GetNumericAttribute(UMyAttributeSet::GetManaAttribute()) < Amount) return false;
    if (Amount == 0.f) return true;
    FGameplayEffectSpec Spec(GetDefault<UPureMassManaEffect>(), ASC->MakeEffectContext(), 1.f);
    Spec.SetSetByCallerMagnitude(UPureMassManaEffect::GetManaTag(), -Amount);
    return ASC->ApplyGameplayEffectSpecToSelf(Spec).WasSuccessfullyApplied();
}

void UPureMassAbility::ApplyCost(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation) const
{
    if (Info && Info->IsNetAuthority() && Prototype) SpendMana(Info->AvatarActor.Get(), Prototype->ManaCost);
}

void UPureMassAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation, const FGameplayEventData* Event)
{
    bTargetConsumed = false;
    MassRuntime = nullptr;
    if (!Info || !Prototype || !GetWorld()->GetSubsystem<UPureMassSubsystem>()) { AbortMass(); return; }
    if (Prototype->Kind == EAbilityPrototypeKind::Beam)
    {
        auto* Release = UAbilityTask_WaitInputRelease::WaitInputRelease(this, true);
        Release->OnRelease.AddDynamic(this, &ThisClass::Released);
        Release->ReadyForActivation();
        if (!IsActive()) return;
    }
    if (Prototype->bTargetSelf || IsInputToggleAbility())
    {
        if (Info->IsNetAuthority()) ExecuteMass(Info->AvatarActor->GetActorLocation(), INDEX_NONE);
        return;
    }
    GetWorld()->GetTimerManager().SetTimer(MassTargetTimeout, this, &ThisClass::AbortMass, 3.f);
    auto* Task = UPureMassTargetData::Create(this);
    Task->Ready.AddDynamic(this, &ThisClass::TargetReady);
    Task->ReadyForActivation();
}

bool UPureMassAbility::ValidateTarget(AActor* Caster, const UAbilityPrototype* Config, int32 Id, const FVector& Requested, FVector& Resolved)
{
    if (!IsValid(Caster) || !Caster->HasAuthority() || !Config || Requested.ContainsNaN() || Id < INDEX_NONE) return false;
    auto* Mass = Caster->GetWorld()->GetSubsystem<UPureMassSubsystem>();
    if (!Mass) return false;
    Resolved = Requested;
    if (Id != INDEX_NONE)
    {
        FPureMassView View;
        if (!Mass->Resolve(Id, View) || View.Health <= 0.f || View.State == 3) return false;
        // Prevent a valid ID from smuggling an unrelated aim point; allow snapshot interpolation error.
        if (FVector::DistSquared(Requested, View.Location) > FMath::Square(250.f)) return false;
        Resolved = View.Location;
    }
    if (FVector::DistSquared(Caster->GetActorLocation(), Resolved) > FMath::Square(Config->Range)) return false;
    using K = EAbilityPrototypeKind;
    if ((Config->Kind == K::Beam || Config->Kind == K::Homing || Config->Kind == K::Chain) && Id == INDEX_NONE) return false;
    FHitResult Wall;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PureMassValidate), false, Caster);
    const bool bWall = Caster->GetWorld()->LineTraceSingleByChannel(Wall, Caster->GetActorLocation() + FVector(0,0,30), Resolved, ECC_Visibility, Query);
    return !bWall || (Id == INDEX_NONE && FVector::DistSquared(Wall.ImpactPoint, Resolved) <= FMath::Square(15.f));
}

void UPureMassAbility::TargetReady(const FGameplayAbilityTargetDataHandle& Data)
{
    if (!IsActive() || bTargetConsumed || !CurrentActorInfo) return;
    if (!CurrentActorInfo->IsNetAuthority())
    {
        bTargetConsumed = true;
        GetWorld()->GetTimerManager().ClearTimer(MassTargetTimeout);
        return;
    }
    const FHitResult* Hit = Data.Num() == 1 && Data.Get(0) ? Data.Get(0)->GetHitResult() : nullptr;
    FVector Point;
    if (!Hit || !Hit->bBlockingHit || Hit->GetActor() || !ValidateTarget(GetAvatarActorFromActorInfo(), Prototype, Hit->Item, Hit->ImpactPoint, Point))
    { AbortMass(); return; }
    ExecuteMass(Point, Hit->Item);
}

void UPureMassAbility::ExecuteMass(const FVector& Point, int32 Id)
{
    if (bTargetConsumed || !IsActive() || !CurrentActorInfo->IsNetAuthority()) return;
    bTargetConsumed = true;
    GetWorld()->GetTimerManager().ClearTimer(MassTargetTimeout);
    AActor* Avatar = GetAvatarActorFromActorInfo();
    FVector Origin = Point;
    using K = EAbilityPrototypeKind;
    if (Prototype->Kind == K::Surface && !APrototypeRuntime::ProjectSurfaceToGround(Avatar, Point, Origin)) { AbortMass(); return; }
    if (!CanActivateAbility(CurrentSpecHandle, CurrentActorInfo) || !CommitAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo))
    { AbortMass(); return; }
    auto* Context = NewObject<UPrototypeCastContext>(Avatar);
    Context->Caster = Avatar;
    Context->CastId = FGuid::NewGuid();
    Context->Level = GetAbilityLevel();
    Context->DamageParams = MakeDamageEffectParamsFromClassDefaults();
    FVector Direction = (Point - Avatar->GetActorLocation()).GetSafeNormal(SMALL_NUMBER, Avatar->GetActorForwardVector());
    if (Prototype->Kind == K::Projectile || Prototype->Kind == K::Multishot || Prototype->Kind == K::Homing || Prototype->Kind == K::Piercing || Prototype->Kind == K::Returning)
    {
        Origin = Avatar->GetActorLocation() + FVector(0,0,30);
        Direction = (Point + (Id == INDEX_NONE ? FVector(0,0,30) : FVector::ZeroVector) - Origin).GetSafeNormal(SMALL_NUMBER, Direction);
    }
    if (Prototype->Kind == K::Cone || Prototype->Kind == K::Line || Prototype->Kind == K::Chain) Origin = Avatar->GetActorLocation();
    MassRuntime = APureMassRuntime::Spawn(Context, Prototype, Origin, Direction, Id);
    if (!IsValid(MassRuntime)) { AbortMass(); return; }
    if (Prototype->Kind != K::Orbit) APureMassRuntime::NotifyCommittedAttack(Avatar, this, Id);
    if (Prototype->Kind == K::Beam || Prototype->Kind == K::Orbit)
        MassRuntime->OnDestroyed.AddDynamic(this, &ThisClass::RuntimeDestroyed);
    else
    {
        MassRuntime = nullptr;
        EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, false);
    }
}

void UPureMassAbility::Released(float) { AbortMass(); }
void UPureMassAbility::RuntimeDestroyed(AActor*)
{
    MassRuntime = nullptr;
    if (IsActive()) EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, false);
}
void UPureMassAbility::AbortMass()
{
    if (IsActive()) EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, true);
}
void UPureMassAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation, bool bReplicate, bool bCancelled)
{
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(MassTargetTimeout);
    if (IsValid(MassRuntime))
    {
        MassRuntime->OnDestroyed.RemoveDynamic(this, &ThisClass::RuntimeDestroyed);
        MassRuntime->CancelCast();
    }
    MassRuntime = nullptr;
    Super::EndAbility(Handle, Info, Activation, bReplicate, bCancelled);
}
