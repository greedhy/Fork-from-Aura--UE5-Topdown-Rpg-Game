#include "AbilitySystem/Prototypes/PrototypeAbility.h"
#include "AbilitySystem/Prototypes/PrototypeFacing.h"
#include "AbilitySystem/Prototypes/AbilityPrototype.h"
#include "AbilitySystem/Prototypes/PrototypeRuntime.h"
#include "AbilitySystem/AbilityTask/TargetDataUnderMouse.h"
#include "AbilitySystem/MyAttributeSet.h"
#include "AbilitySystemComponent.h"
#include "Abilities/Tasks/AbilityTask_WaitInputRelease.h"
#include "TimerManager.h"
#include "AbilitySystem/Data/OrbitingFireBoltConfig.h"

UPrototypeAbility::UPrototypeAbility()
{
    InstancingPolicy = EGameplayAbilityInstancingPolicy::InstancedPerActor;
    NetExecutionPolicy = EGameplayAbilityNetExecutionPolicy::LocalPredicted;
    DebuffChance = 0.f;
    KnockbackChance = 0.f;
    KnockbackForceMagnitude = 0.f;
    DeathImpulseMagnitude = 0.f;
    bIsRadialDamage = false;
}

UPrototypeCooldownEffect::UPrototypeCooldownEffect()
{
    DurationPolicy = EGameplayEffectDurationType::HasDuration;
    DurationMagnitude = FScalableFloat(1.f);
}

bool UPrototypeAbility::IsInputToggleAbility() const
{
    return Prototype && Prototype->Kind == EAbilityPrototypeKind::Orbit;
}

bool UPrototypeAbility::CanActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
    const FGameplayTagContainer* Source, const FGameplayTagContainer* Target, FGameplayTagContainer* Relevant) const
{
    if (!Prototype || !Prototype->IsValidConfiguration() || !DamageEffectClass || !Info || !Info->AvatarActor.IsValid()) return false;
    AActor* Avatar = Info->AvatarActor.Get();
    return Avatar->Implements<UCombatInterface>() && !ICombatInterface::Execute_IsDead(Avatar)
        && Super::CanActivateAbility(Handle, Info, Source, Target, Relevant);
}

bool UPrototypeAbility::CheckCost(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, FGameplayTagContainer* Relevant) const
{
    auto* ASC = Info ? Info->AbilitySystemComponent.Get() : nullptr;
    return Prototype && ASC && ASC->HasAttributeSetForAttribute(UMyAttributeSet::GetManaAttribute())
        && ASC->GetNumericAttribute(UMyAttributeSet::GetManaAttribute()) >= Prototype->ManaCost;
}

void UPrototypeAbility::ApplyCost(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, FGameplayAbilityActivationInfo Activation) const
{
    if (Info && Info->IsNetAuthority()) APrototypeRuntime::SpendMana(Info->AvatarActor.Get(), Prototype->ManaCost);
}

bool UPrototypeAbility::CheckCooldown(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, FGameplayTagContainer* Relevant) const
{
    return Prototype && Info && Info->AbilitySystemComponent.IsValid()
        && (!Prototype->CooldownTag.IsValid() || !Info->AbilitySystemComponent->HasMatchingGameplayTag(Prototype->CooldownTag));
}

void UPrototypeAbility::ApplyCooldown(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info, FGameplayAbilityActivationInfo Activation) const
{
    if (!Info || !Info->IsNetAuthority() || Prototype->Cooldown <= 0.f) return;
    auto* ASC = Info->AbilitySystemComponent.Get();
    FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(UPrototypeCooldownEffect::StaticClass(), GetAbilityLevel(), ASC->MakeEffectContext());
    Spec.Data->SetDuration(Prototype->Cooldown, true);
    Spec.Data->DynamicGrantedTags.AddTag(Prototype->CooldownTag);
    ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
}

void UPrototypeAbility::ActivateAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation, const FGameplayEventData* Event)
{
    bReceivedTarget = false;
    Runtime = nullptr;
    if (!Info || !Prototype) { Abort(); return; }
    if (Prototype->Kind == EAbilityPrototypeKind::Beam)
    {
        auto* Release = UAbilityTask_WaitInputRelease::WaitInputRelease(this, true);
        Release->OnRelease.AddDynamic(this, &ThisClass::OnReleased);
        Release->ReadyForActivation();
        if (!IsActive()) return;
    }
    if (Prototype->bTargetSelf || IsInputToggleAbility())
    {
        if (Info->IsNetAuthority()) Execute(Info->AvatarActor->GetActorLocation(), nullptr);
        return;
    }
    GetWorld()->GetTimerManager().SetTimer(TargetTimeout, this, &ThisClass::Abort, 3.f);
    auto* Task = UTargetDataUnderMouse::CreateTargetDataUnderMouse(this);
    Task->ValidData.AddDynamic(this, &ThisClass::OnTargetData);
    Task->ReadyForActivation();
}

void UPrototypeAbility::OnTargetData(const FGameplayAbilityTargetDataHandle& Data)
{
    if (!IsActive() || bReceivedTarget) return;
    if (!CurrentActorInfo->IsNetAuthority())
    {
        bReceivedTarget = true;
        GetWorld()->GetTimerManager().ClearTimer(TargetTimeout);
        return;
    }
    const FHitResult* Hit = Data.Num() == 1 && Data.Get(0) ? Data.Get(0)->GetHitResult() : nullptr;
    if (!Hit || !Hit->bBlockingHit || Hit->ImpactPoint.ContainsNaN()) { Abort(); return; }
    AActor* Avatar = GetAvatarActorFromActorInfo();
    AActor* Target = APrototypeRuntime::IsEnemy(Avatar, Hit->GetActor()) ? Hit->GetActor() : nullptr;
    const FVector Position = Target ? Target->GetActorLocation() : FVector(Hit->ImpactPoint);
    if (Prototype->Kind == EAbilityPrototypeKind::Line)
    {
        // A Line uses the finite cursor point only as a direction request. The server's
        // ShapePulse enforces length, width, height and visibility per affected enemy.
        Execute(Position, Target);
        return;
    }
    if (FVector::DistSquared(Avatar->GetActorLocation(), Position) > FMath::Square(Prototype->Range)) { Abort(); return; }
    FHitResult Obstruction;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PrototypeAim), false, Avatar);
    // Validate against server geometry; the cursor result is only an aiming request.
    if (GetWorld()->LineTraceSingleByChannel(Obstruction, Avatar->GetActorLocation() + FVector(0,0,30), Position,
        ECC_Visibility, Query) && Obstruction.GetActor() != Target && FVector::DistSquared(Obstruction.ImpactPoint, Position) > FMath::Square(50.f))
    { Abort(); return; }
    if ((Prototype->Kind == EAbilityPrototypeKind::Beam || Prototype->Kind == EAbilityPrototypeKind::Homing
        || Prototype->Kind == EAbilityPrototypeKind::Chain) && !Target) { Abort(); return; }
    Execute(Position, Target);
}

void UPrototypeAbility::Execute(const FVector& Position, AActor* Target)
{
    if (bReceivedTarget || !IsActive()) return;
    bReceivedTarget = true;
    GetWorld()->GetTimerManager().ClearTimer(TargetTimeout);
    AActor* Avatar = GetAvatarActorFromActorInfo();
    FVector Origin = Position;
    if (Prototype->Kind == EAbilityPrototypeKind::Surface
        && !APrototypeRuntime::ProjectSurfaceToGround(Avatar,Position,Origin)) { Abort(); return; }
    SetOffensiveAttackTarget(Target);
    if (!CanActivateAbility(CurrentSpecHandle, CurrentActorInfo) || !CommitAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo))
    { Abort(); return; }
    auto* Context = NewObject<UPrototypeCastContext>(Avatar);
    Context->Caster = Avatar;
    Context->CastId = FGuid::NewGuid();
    Context->Level = GetAbilityLevel();
    Context->DamageParams = MakeDamageEffectParamsFromClassDefaults();
    FVector Direction = (Position - Avatar->GetActorLocation()).GetSafeNormal();
    if (Direction.IsNearlyZero()) Direction = Avatar->GetActorForwardVector();
    using K = EAbilityPrototypeKind;
    if (Prototype->Kind == K::Projectile || Prototype->Kind == K::Multishot
        || Prototype->Kind == K::Homing || Prototype->Kind == K::Piercing)
    {
        Origin = Avatar->GetActorLocation() + FVector(0,0,30) + Direction * 60.f;
        Direction = ((Target ? Position : Position + FVector(0,0,30)) - Origin).GetSafeNormal();
    }
    if (Prototype->Kind == K::Chain) Origin = Avatar->GetActorLocation() + FVector(0,0,30);
    if (Prototype->Kind == K::Cone || Prototype->Kind == K::Line) Origin = Avatar->GetActorLocation();
    if (Prototype->Kind == K::Returning)
    {
        Direction=(Position-Avatar->GetActorLocation()).GetSafeNormal2D(SMALL_NUMBER,Avatar->GetActorForwardVector());
        Origin=Avatar->GetActorLocation()+Direction*60.f;
        if (Target) Origin.Z=Position.Z;
    }
    Runtime = APrototypeRuntime::Spawn(Context, Prototype, Origin, Direction, Target);
    if (!IsValid(Runtime)) { Abort(); return; }
    PrototypeFacing::Apply(Avatar, Position, Prototype->bTargetSelf);
    if (Prototype->Kind == K::Beam || Prototype->Kind == K::Orbit)
        Runtime->OnDestroyed.AddDynamic(this, &ThisClass::OnRuntimeDestroyed);
    else
    {
        Runtime = nullptr; // Finite actors own their lifespan after an instant GA ends.
        EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, false);
    }
}

void UPrototypeAbility::OnReleased(float) { Abort(); }
void UPrototypeAbility::OnRuntimeDestroyed(AActor*)
{
    Runtime = nullptr;
    if (IsActive()) EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, false);
}
void UPrototypeAbility::Abort()
{
    if (IsActive()) EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, true);
}
void UPrototypeAbility::EndAbility(FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* Info,
    FGameplayAbilityActivationInfo Activation, bool bReplicate, bool bCancelled)
{
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(TargetTimeout);
    if (IsValid(Runtime))
    {
        Runtime->OnDestroyed.RemoveDynamic(this, &ThisClass::OnRuntimeDestroyed);
        Runtime->CancelCast();
    }
    Runtime = nullptr;
    Super::EndAbility(Handle, Info, Activation, bReplicate, bCancelled);
}

FString UPrototypeAbility::GetDescription(int32 Level)
{
    if (!Prototype) return TEXT("<Default>Missing prototype configuration</>");
    const auto& P = *Prototype;
    const float HitDamage = P.DamageAtLevel(Level);
    FString Detail;
    using K = EAbilityPrototypeKind;
    switch (P.Kind)
    {
    case K::Projectile: Detail = FString::Printf(TEXT("One shot: %.0f damage. Range %.0f."),HitDamage,P.Range); break;
    case K::Multishot: Detail = FString::Printf(TEXT("%d shots, %.0f-degree fan. %.0f damage each."),P.Count,P.SpreadDegrees,HitDamage); break;
    case K::Burst: Detail = FString::Printf(TEXT("Burst: %.0f damage. Radius %.0f."),HitDamage,P.Radius); break;
    case K::Beam: Detail = FString::Printf(TEXT("Hold: %.0f damage/%.1fs, %.0f MP/s. Up to %.0fs."),HitDamage,P.Period,P.ManaPerSecond,P.Duration); break;
    case K::Surface: Detail = FString::Printf(TEXT("Enemy-only ground: %.0fx%.0f, lasts %.0fs."),P.Radius*2,P.Radius*2,P.Duration); break;
    case K::Orbit:
        Detail = P.OrbitSettings ? FString::Printf(TEXT("Toggle: %.0f MP/s. One bolt/%.1fs; cap %d."),P.ManaPerSecond,P.OrbitSettings->SpawnInterval,P.OrbitSettings->MaxFireBolts) : TEXT("Missing orbit settings."); break;
    case K::Field: Detail = FString::Printf(TEXT("%.0f damage/%.1fs, radius %.0f. Lasts %.0fs."),HitDamage,P.Period,P.Radius,P.Duration); break;
    case K::Trap: Detail = FString::Printf(TEXT("Arms in %.1fs: %.0f damage. Lasts %.0fs."),P.ArmDelay,HitDamage,P.Duration); break;
    case K::Homing: Detail = FString::Printf(TEXT("Tracks one enemy: %.0f damage. Range %.0f."),HitDamage,P.Range); break;
    case K::Piercing: Detail = FString::Printf(TEXT("Pierces %d foes: %.0f damage, %.0f%% per hit."),P.Count,HitDamage,P.DamageFalloff*100); break;
    case K::Chain: Detail = FString::Printf(TEXT("%d foes: %.0f damage, %.0f%% per hop."),P.Count,HitDamage,P.DamageFalloff*100); break;
    case K::Cone: Detail = FString::Printf(TEXT("%.0f-degree arc, radius %.0f. %.0f damage."),P.SpreadDegrees,P.Radius,HitDamage); break;
    case K::Wave: Detail = FString::Printf(TEXT("Expands to %.0f: %.0f damage, once per foe."),P.Radius,HitDamage); break;
    case K::Returning: Detail = FString::Printf(TEXT("Out: %.0f damage. Return: %.0f%%. %d foes/pass."),HitDamage,P.DamageFalloff*100,P.Count); break;
    case K::Emitter: Detail = FString::Printf(TEXT("Auto-fire every %.1fs. Up to %d shots."),P.Period,P.Count); break;
    case K::Delay: Detail = FString::Printf(TEXT("After %.1fs: %s"),P.ArmDelay,P.OnExpire ? *P.OnExpire->DisplayName.ToString().Left(24) : TEXT("Missing child")); break;
    case K::Ring: Detail = FString::Printf(TEXT("Ring %.0f-%.0f: %.0f damage."),P.InnerRadius,P.Radius,HitDamage); break;
    case K::Line: Detail = FString::Printf(TEXT("Line %.0fx%.0f: %.0f damage."),P.Range,P.Width,HitDamage); break;
    }
    if ((P.OnHit || P.OnExpire || P.OnPeriod) && P.Kind != K::Emitter && P.Kind != K::Delay)
    {
        const UAbilityPrototype* Child = P.OnHit ? P.OnHit.Get() : P.OnExpire ? P.OnExpire.Get() : P.OnPeriod.Get();
        const TCHAR* Trigger = P.OnHit ? TEXT("Hit") : P.OnExpire ? TEXT("End") : TEXT("Tick");
        Detail += FString::Printf(TEXT(" %s: %s"),Trigger,*Child->DisplayName.ToString().Left(24));
    }
    return FString::Printf(TEXT("<Title>%s</>\n<Small>Lv.%d | MP %.0f | CD %.1fs</>\n<Default>%s</>"),
        *P.DisplayName.ToString(), Level, P.ManaCost, P.Cooldown, *Detail);
}
FString UPrototypeAbility::GetNextLevelDescription(int32 Level) { return GetDescription(Level); }
