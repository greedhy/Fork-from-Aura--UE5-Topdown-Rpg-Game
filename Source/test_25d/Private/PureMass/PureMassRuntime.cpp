#include "PureMass/PureMassRuntime.h"
#include "PureMass/PureMassAbility.h"
#include "PureMass/PureMassSubsystem.h"
#include "AbilitySystem/Prototypes/PrototypeRuntime.h"
#include "AbilitySystem/Data/OrbitingFireBoltConfig.h"
#include "AbilitySystem/Ability/MyDamageGameplayAbility.h"
#include "AbilitySystem/MyAbilitySystemLibrary.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Terrain/TerrainSurface.h"
#include "Interface/CombatInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Net/UnrealNetwork.h"

APureMassRuntime::APureMassRuntime()
{
    bReplicates = true;
    SetReplicateMovement(true);
    SetNetUpdateFrequency(30.f);
    PrimaryActorTick.bCanEverTick = true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    Visual = CreateDefaultSubobject<UNiagaraComponent>(TEXT("Visual"));
    Visual->SetupAttachment(RootComponent);
    Visual->SetAutoActivate(false);
}

APureMassRuntime* APureMassRuntime::Spawn(UPrototypeCastContext* InContext, UAbilityPrototype* Config,
    FVector Position, FVector InDirection, FPureMassCombatTarget InTarget, int32 InDepth, bool bInSingle)
{
    AActor* Caster = InContext ? InContext->Caster.Get() : nullptr;
    if (!IsValid(Caster) || !Caster->HasAuthority() || !Config || !Config->IsValidConfiguration()
        || Position.ContainsNaN() || InDirection.ContainsNaN()) return nullptr;
    if (Caster->Implements<UCombatInterface>() && ICombatInterface::Execute_IsDead(Caster)) return nullptr;
    if (Config->Kind == EAbilityPrototypeKind::Surface && !APrototypeRuntime::ProjectSurfaceToGround(Caster, Position, Position)) return nullptr;
    if (!InContext->ReserveSpawn(InDepth)) return nullptr;
    InDirection = InDirection.GetSafeNormal(SMALL_NUMBER, FVector::ForwardVector);
    const FTransform Transform(InDirection.Rotation(), Position);
    auto* R = Caster->GetWorld()->SpawnActorDeferred<APureMassRuntime>(StaticClass(), Transform, Caster,
        Cast<APawn>(Caster), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if (!R) return nullptr;
    R->Context = InContext;
    R->Prototype = Config;
    R->Direction = InDirection;
    R->ChainOrigin = Position;
    R->Target = InTarget;
    R->Depth = InDepth;
    R->bSingle = bInSingle;
    R->BeamEnd = Position + InDirection * Config->Range;
    R->FinishSpawning(Transform);
    return R;
}

void APureMassRuntime::BeginPlay()
{
    Super::BeginPlay();
    RefreshVisual();
    if (!HasAuthority() || !Context || !Prototype) return;
    using K = EAbilityPrototypeKind;
    switch (Prototype->Kind)
    {
    case K::Multishot:
        if (!bSingle)
        {
            for (int32 I = 0; I < Prototype->Count; ++I)
            {
                const float Angle = Prototype->Count == 1 ? 0.f : -Prototype->SpreadDegrees * .5f + Prototype->SpreadDegrees * I / (Prototype->Count - 1);
                Spawn(Context, Prototype, GetActorLocation(), Direction.RotateAngleAxis(Angle, FVector::UpVector), INDEX_NONE, Depth, true);
            }
            // Each pellet owns its hit/expiry hooks. The fan container has no hooks.
            bFinished = true;
            RefreshVisual();
            SetLifeSpan(.35f);
        }
        break;
    case K::Burst: case K::Cone: case K::Ring: case K::Line:
        Pulse();
        break;
    case K::Surface:
    {
        const FTransform Transform(FRotator::ZeroRotator, GetActorLocation());
        Surface = GetWorld()->SpawnActorDeferred<ATerrainSurface>(Prototype->SurfaceClass, Transform, GetOwner(),
            Cast<APawn>(GetOwner()), ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if (!Surface) { Finish(true); break; }
        Surface->bOnlyAffectCasterEnemies = true;
        Surface->bAffectPlayers = false;
        Surface->bAffectEnemies = true;
        Surface->SurfaceSize = FVector2D(Prototype->Radius * 2.f);
        Surface->FinishSpawning(Transform);
        if (Surface->Ground) Surface->Ground->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        break;
    }
    default: break;
    }
}

bool APureMassRuntime::Visible(FVector Origin, const FPureMassCombatTarget& Candidate) const
{
    return PureMassCombat::Visible(GetWorld(), GetOwner(), Origin, Candidate, const_cast<APureMassRuntime*>(this));
}

bool APureMassRuntime::Hit(FPureMassCombatTarget Candidate, float Scale)
{
    if (!HasAuthority() || !Context || Context->bCancelled || bFinished || !Prototype) return false;
    AActor* Caster = Context->Caster.Get();
    if (!IsValid(Caster) || (Caster->Implements<UCombatInterface>() && ICombatInterface::Execute_IsDead(Caster))) return false;
    FVector Position;
    if (!PureMassCombat::Resolve(GetWorld(), Context->Caster.Get(), Candidate, Position)) return false;
    if (Candidate.IsActor())
    {
        FDamageEffectParams Params = Context->DamageParams;
        Params.WorldContextObject = this;
        Params.TargetAbilitySystemComponent = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Candidate.Actor.Get());
        if (!IsValid(Params.SourceAbilitySystemComponent))
            Params.SourceAbilitySystemComponent = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Context->Caster.Get());
        if (!IsValid(Params.SourceAbilitySystemComponent) || !IsValid(Params.TargetAbilitySystemComponent)
            || !Params.DamageGameplayEffectClass) return false;
        if (Params.SourceAbilitySystemComponent->GetAvatarActor() != Context->Caster.Get()
            || Params.SourceAbilitySystemComponent->GetWorld() != GetWorld()) return false;
        Params.BaseDamage = Prototype->DamageAtLevel(Context->Level) * Scale;
        Params.DamageType = Prototype->DamageType;
        Params.bIsRadialDamage = false;
        UMyAbilitySystemLibrary::ApplyDamageEffect(Params);
    }
    else
    {
        auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
        if (!Mass) return false;
        FPureMassDamage Damage;
        Damage.Source = Context->Caster;
        Damage.Amount = Prototype->DamageAtLevel(Context->Level) * Scale;
        Damage.DamageType = Prototype->DamageType;
        const auto& Params = Context->DamageParams;
        if (Params.DebuffChance > 0.f && FMath::FRandRange(0.f,100.f) < Params.DebuffChance)
        {
            Damage.StatusDuration = Params.DebuffDuration;
            Damage.DamagePerSecond = Params.DebuffDamage / FMath::Max(.1f, Params.DebuffFrequency);
        }
        Mass->ApplyDamage(Candidate.EntityId, Damage);
    }
    Impact(Position);
    Emit(Prototype->OnHit, Position, Candidate);
    return true;
}

bool APureMassRuntime::Emit(UAbilityPrototype* Child, FVector Position, FPureMassCombatTarget Candidate)
{
    return HasAuthority() && Context && !Context->bCancelled && Child
        && Spawn(Context, Child, Position, Direction, Candidate, Depth + 1) != nullptr;
}

FPureMassCombatTarget APureMassRuntime::Nearest(FVector Origin, float Radius) const
{
    float Best = FMath::Square(Radius);
    FPureMassCombatTarget Result;
    for (const auto& Candidate : PureMassCombat::Gather(GetWorld(), GetOwner(), Origin, Radius))
    {
        FVector Position;
        if (HitTargets.Contains(Candidate) || !PureMassCombat::Resolve(GetWorld(), GetOwner(), Candidate, Position)) continue;
        const float Dist = FVector::DistSquared(Origin, Position);
        if (Dist <= Best && Visible(Origin, Candidate)) { Result = Candidate; Best = Dist; }
    }
    return Result;
}

void APureMassRuntime::Pulse()
{
    using K = EAbilityPrototypeKind;
    const auto Kind = Prototype->Kind;
    const FVector Facing = Direction.GetSafeNormal2D(SMALL_NUMBER, FVector::ForwardVector);
    const FVector Right = FVector::CrossProduct(FVector::UpVector, Facing);
    const float Bounds = Kind == K::Line ? FMath::Sqrt(FMath::Square(Prototype->Range) + FMath::Square(Prototype->Width*.5f) + FMath::Square(Prototype->ShapeHalfHeight))
        : Kind == K::Ring ? FMath::Sqrt(FMath::Square(Prototype->Radius) + FMath::Square(Prototype->ShapeHalfHeight)) : Prototype->Radius;
    for (const auto& Candidate : PureMassCombat::Gather(GetWorld(), GetOwner(), GetActorLocation(), Bounds))
    {
        FVector Position;
        if (!PureMassCombat::Resolve(GetWorld(), GetOwner(), Candidate, Position)) continue;
        const FVector Offset = Position - GetActorLocation();
        if (Kind == K::Cone && !Offset.IsNearlyZero()
            && FVector::DotProduct(Facing, Offset.GetSafeNormal2D()) < FMath::Cos(FMath::DegreesToRadians(Prototype->SpreadDegrees * .5f))) continue;
        if ((Kind == K::Line || Kind == K::Ring) && FMath::Abs(Offset.Z) > Prototype->ShapeHalfHeight) continue;
        if (Kind == K::Ring && (Offset.SizeSquared2D() < FMath::Square(Prototype->InnerRadius) || Offset.SizeSquared2D() > FMath::Square(Prototype->Radius))) continue;
        if (Kind == K::Line)
        {
            const float Along = FVector::DotProduct(Facing, Offset);
            if (Along < 0.f || Along > Prototype->Range || FMath::Abs(FVector::DotProduct(Right, Offset)) > Prototype->Width * .5f) continue;
        }
        if (Kind == K::Wave && (HitTargets.Contains(Candidate) || Offset.SizeSquared() > FMath::Square(WaveRadius))) continue;
        if (!Visible(GetActorLocation(), Candidate)) continue;
        Hit(Candidate);
        if (Kind == K::Wave) HitTargets.Add(Candidate);
    }
}

void APureMassRuntime::Projectile(float Delta)
{
    using K = EAbilityPrototypeKind;
    const bool bReturn = Prototype->Kind == K::Returning;
    float Remaining = FMath::Max(0.f, Prototype->Range - Travel);
    if (bReturn && bReturning)
    {
        Remaining = FVector::Distance(GetActorLocation(), GetOwner()->GetActorLocation());
        if (Remaining <= Prototype->CollisionRadius) { Finish(false); return; }
        Direction = (GetOwner()->GetActorLocation() - GetActorLocation()).GetSafeNormal();
    }
    if (Prototype->Kind == K::Homing)
    {
        FVector Position;
        if (!PureMassCombat::Resolve(GetWorld(), GetOwner(), Target, Position)) { Finish(false); return; }
        Direction = FMath::VInterpNormalRotationTo(Direction, (Position - GetActorLocation()).GetSafeNormal(), Delta, Prototype->HomingTurnRate);
    }
    const float Step = FMath::Min(Prototype->Speed * Delta, Remaining);
    const FVector Start = GetActorLocation(), End = Start + Direction * Step;
    FHitResult Wall;
    // Re-query both representations with the growing exclusion set; walls still win ties.
    for (int32 I = 0; I < 64; ++I)
    {
        float Time = 1.f;
        const auto Candidate = PureMassCombat::Sweep(GetWorld(), GetOwner(), Start, End,
            Prototype->CollisionRadius, Time, Wall, &HitTargets, this);
        if (!Candidate.IsSet()) break;
        if (bReturn && HitTargets.Num() >= Prototype->Count) break;
        SetActorLocation(FMath::Lerp(Start, End, Time));
        Hit(Candidate, bReturn ? (bReturning ? Prototype->DamageFalloff : 1.f) : FMath::Pow(Prototype->DamageFalloff, HitTargets.Num()));
        HitTargets.Add(Candidate);
        if (!bReturn && (Prototype->Kind != K::Piercing || HitTargets.Num() >= Prototype->Count)) { Finish(false); return; }
    }
    if (Wall.bBlockingHit) { SetActorLocation(Wall.Location); Impact(Wall.ImpactPoint); Finish(false); return; }
    SetActorLocation(End);
    SetActorRotation(Direction.Rotation());
    Travel += Step;
    if (bReturn)
    {
        if (bReturning && Step >= Remaining) { Finish(false); return; }
        if (!bReturning && Travel >= Prototype->Range)
        {
            bReturning = true;
            HitTargets.Reset();
            const float Remainder = Delta - Step / Prototype->Speed;
            if (Remainder > SMALL_NUMBER) Projectile(Remainder);
        }
    }
    else if (Travel >= Prototype->Range) Finish(false);
}

void APureMassRuntime::Chain()
{
    FVector Position;
    const float Reach = HitTargets.IsEmpty() ? Prototype->Range : Prototype->Radius;
    if (HitTargets.Num() >= Prototype->Count || HitTargets.Contains(Target) || !PureMassCombat::Resolve(GetWorld(), GetOwner(), Target, Position)
        || FVector::DistSquared(ChainOrigin, Position) > FMath::Square(Reach) || !Visible(ChainOrigin, Target))
    { Finish(false); return; }
    SetActorLocation(ChainOrigin);
    BeamEnd = Position;
    Hit(Target, FMath::Pow(Prototype->DamageFalloff, HitTargets.Num()));
    HitTargets.Add(Target);
    ChainOrigin = Position;
    Target = Nearest(Position, Prototype->Radius);
    ForceNetUpdate();
    if (!Target.IsSet() || HitTargets.Num() >= Prototype->Count) Finish(false);
}

void APureMassRuntime::NotifyCommittedAttack(AActor* Caster, UGameplayAbility* Ability, FPureMassCombatTarget Candidate)
{
    auto* DamageAbility = Cast<UMyDamageGameplayAbility>(Ability);
    if (!IsValid(Caster) || !Caster->HasAuthority() || !DamageAbility || !DamageAbility->HasCommittedOffensiveAttack()) return;
    FVector Position;
    if (!PureMassCombat::Resolve(Caster->GetWorld(), Caster, Candidate, Position)) return;
    for (TActorIterator<APureMassRuntime> It(Caster->GetWorld()); It; ++It)
        if (It->GetOwner() == Caster && !It->bFinished && It->Prototype && It->Prototype->Kind == EAbilityPrototypeKind::Orbit
            && It->Prototype->OrbitSettings && FVector::DistSquared(Caster->GetActorLocation(), Position) <= FMath::Square(It->Prototype->OrbitSettings->MaxTargetDistance))
            It->Target = Candidate;
}

void APureMassRuntime::Orbit(float Delta)
{
    const auto* Settings = Prototype->OrbitSettings.Get();
    if (!Settings) { Finish(true); return; }
    SetActorLocation(GetOwner()->GetActorLocation());
    PeriodClock += Delta;
    LaunchClock += Delta;
    if (PeriodClock >= Settings->SpawnInterval)
    {
        PeriodClock = FMath::Fmod(PeriodClock, Settings->SpawnInterval);
        if (OrbitBolts.Num() < Settings->MaxFireBolts)
        {
            const int32 Index = OrbitBolts.AddDefaulted();
            const float Angle = Age * Settings->OrbitDegreesPerSecond + 360.f * Index / OrbitBolts.Num();
            // Launch can happen this same tick. Never expose the default world-origin position to its sweep.
            OrbitBolts[Index].Position = GetActorLocation()
                + FVector(Settings->OrbitRadius, 0, Settings->OrbitHeight).RotateAngleAxis(Angle, FVector::UpVector);
        }
        Emit(Prototype->OnPeriod, GetActorLocation(), Target);
    }
    FVector TargetPosition;
    const bool bTarget = PureMassCombat::Resolve(GetWorld(), GetOwner(), Target, TargetPosition)
        && FVector::DistSquared(GetActorLocation(), TargetPosition) <= FMath::Square(Settings->MaxTargetDistance);
    if (!bTarget) Target = {};
    if (bTarget && LaunchClock >= Settings->LaunchInterval && Visible(GetActorLocation(), Target))
    {
        for (auto& Bolt : OrbitBolts) if (!Bolt.bLaunched) { Bolt.bLaunched = true; Bolt.Age = 0.f; LaunchClock = 0.f; break; }
    }
    for (int32 I = OrbitBolts.Num() - 1; I >= 0; --I)
    {
        auto& Bolt = OrbitBolts[I];
        if (!bTarget) { Bolt.bLaunched = false; Bolt.Age = 0.f; }
        if (!Bolt.bLaunched)
        {
            const float Angle = Age * Settings->OrbitDegreesPerSecond + 360.f * I / FMath::Max(1, OrbitBolts.Num());
            Bolt.Position = GetActorLocation() + FVector(Settings->OrbitRadius, 0, Settings->OrbitHeight).RotateAngleAxis(Angle, FVector::UpVector);
            continue;
        }
        Bolt.Age += Delta;
        const FVector Start = Bolt.Position;
        const FVector End = FMath::VInterpConstantTo(Start, TargetPosition, Delta, Settings->ProjectileSpeed);
        float Time = 1.f;
        FHitResult Wall;
        const auto Candidate = PureMassCombat::Sweep(GetWorld(), GetOwner(), Start, End,
            Prototype->CollisionRadius, Time, Wall, nullptr, this);
        if (Candidate.IsSet()) { Hit(Candidate); OrbitBolts.RemoveAt(I); continue; }
        if (Wall.bBlockingHit || Bolt.Age >= Settings->MaxFlightSeconds) { OrbitBolts.RemoveAt(I); continue; }
        Bolt.Position = End;
    }
}

void APureMassRuntime::Tick(float Delta)
{
    Super::Tick(Delta);
    if (Prototype && GetNetMode() != NM_DedicatedServer)
    {
        Visual->SetVariableVec3(TEXT("BeamEnd"), BeamEnd);
        Visual->SetVariableVec3(TEXT("User.BeamEnd"), BeamEnd);
        Visual->SetVariableVec3(TEXT("Beam Start"), GetActorLocation());
        Visual->SetVariableVec3(TEXT("Beam End"), BeamEnd);
        if (Prototype->Kind == EAbilityPrototypeKind::Wave) Visual->SetRelativeScale3D(FVector(FMath::Max(.05f, WaveRadius / 100.f)));
        while (BoltVisuals.Num() < OrbitBolts.Num())
        {
            auto* V = NewObject<UNiagaraComponent>(this);
            V->SetupAttachment(RootComponent); V->RegisterComponent(); V->SetAsset(Prototype->LoopVFX); V->Activate(true);
            BoltVisuals.Add(V);
        }
        for (int32 I = 0; I < BoltVisuals.Num(); ++I)
        {
            BoltVisuals[I]->SetVisibility(!bFinished && OrbitBolts.IsValidIndex(I));
            if (OrbitBolts.IsValidIndex(I)) BoltVisuals[I]->SetWorldLocation(OrbitBolts[I].Position);
        }
    }
    if (!HasAuthority() || bFinished) return;
    if (!Context || Context->bCancelled || !Prototype || !IsValid(GetOwner())
        || (GetOwner()->Implements<UCombatInterface>() && ICombatInterface::Execute_IsDead(GetOwner()))) { Finish(true); return; }
    Age += Delta;
    using K = EAbilityPrototypeKind;
    const auto Kind = Prototype->Kind;
    if ((Kind == K::Beam || Kind == K::Orbit) && !UPureMassAbility::SpendMana(GetOwner(), Prototype->ManaPerSecond * Delta)) { Finish(true); return; }
    // Orbit is a toggle, finite kinds honor their configured duration.
    if ((Kind != K::Orbit || Depth > 0) && Age >= Prototype->Duration) { Finish(false); return; }
    if (Kind != K::Orbit && Kind != K::Beam && Kind != K::Field && Kind != K::Chain && Kind != K::Emitter)
    {
        PeriodClock += Delta;
        for (int32 I = 0; I < 8 && PeriodClock >= Prototype->Period; ++I)
        {
            PeriodClock -= Prototype->Period;
            if (Kind != K::Burst) Emit(Prototype->OnPeriod, GetActorLocation(), Target);
        }
    }
    if (Kind == K::Projectile || Kind == K::Multishot || Kind == K::Homing || Kind == K::Piercing || Kind == K::Returning)
    { Projectile(Delta); return; }
    if (Kind == K::Orbit) { Orbit(Delta); return; }
    if (Kind == K::Wave)
    {
        WaveRadius = FMath::Min(Prototype->Radius, WaveRadius + Prototype->Speed * Delta);
        Pulse();
        if (WaveRadius >= Prototype->Radius) Finish(false);
        return;
    }
    if (Kind == K::Delay) { if (Age >= Prototype->ArmDelay) Finish(false); return; }
    if (Kind == K::Trap)
    {
        if (Age >= Prototype->ArmDelay && Nearest(GetActorLocation(), Prototype->Radius).IsSet()) { Pulse(); Finish(false); }
        return;
    }
    if (Kind == K::Beam)
    {
        FVector Position;
        if (!PureMassCombat::Resolve(GetWorld(), GetOwner(), Target, Position) || FVector::DistSquared(GetOwner()->GetActorLocation(), Position) > FMath::Square(Prototype->Range)
            || !Visible(GetOwner()->GetActorLocation() + FVector(0,0,30), Target)) { Finish(false); return; }
        SetActorLocation(GetOwner()->GetActorLocation() + FVector(0,0,30));
        BeamEnd = Position;
    }
    if (Kind == K::Beam || Kind == K::Field || Kind == K::Chain || Kind == K::Emitter) PeriodClock += Delta;
    if (Kind == K::Chain && HitTargets.IsEmpty()) { Chain(); PeriodClock = 0.f; return; }
    // At most eight catch-up pulses per frame; no unbounded bursts after a hitch.
    for (int32 I = 0; I < 8 && !bFinished && PeriodClock >= Prototype->Period; ++I)
    {
        PeriodClock -= Prototype->Period;
        if (Kind == K::Chain) { Chain(); continue; }
        if (Kind == K::Field) Pulse();
        if (Kind == K::Beam) Hit(Target);
        if (Kind == K::Emitter)
        {
            Target = Nearest(GetActorLocation(), Prototype->Radius);
            FVector Position;
            if (!PureMassCombat::Resolve(GetWorld(), GetOwner(), Target, Position)) { PeriodClock = 0.f; break; }
            Direction = (Position - GetActorLocation()).GetSafeNormal(SMALL_NUMBER, Direction);
            if (Emit(Prototype->OnPeriod, GetActorLocation(), Target) && ++Emissions >= Prototype->Count) Finish(false);
        }
        else Emit(Prototype->OnPeriod, GetActorLocation(), Target);
    }
}

void APureMassRuntime::Finish(bool bCancelled)
{
    if (bFinished) return;
    bFinished = true;
    if (bCancelled) { if (Context) Context->bCancelled = true; }
    else Emit(Prototype->OnExpire, Prototype->Kind == EAbilityPrototypeKind::Chain ? ChainOrigin : GetActorLocation(), Target);
    if (IsValid(Surface)) Surface->Destroy();
    Surface = nullptr;
    OrbitBolts.Reset();
    RefreshVisual();
    ForceNetUpdate();
    SetLifeSpan(.35f);
}

void APureMassRuntime::CancelCast()
{
    if (!HasAuthority()) return;
    if (Context) Context->bCancelled = true;
    Finish(true);
}

void APureMassRuntime::RefreshVisual()
{
    if (!Prototype || GetNetMode() == NM_DedicatedServer) return;
    if (bFinished)
    {
        Visual->DeactivateImmediate();
        for (const auto& V : BoltVisuals) if (V) V->DeactivateImmediate();
        if (!bPresented && Prototype->ImpactVFX) UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, Prototype->ImpactVFX, GetActorLocation());
        bPresented = true;
        return;
    }
    if (Prototype->LoopVFX && Prototype->Kind != EAbilityPrototypeKind::Orbit && (Prototype->Kind != EAbilityPrototypeKind::Multishot || bSingle))
    { Visual->SetAsset(Prototype->LoopVFX); Visual->Activate(true); }
    if (Prototype->Kind == EAbilityPrototypeKind::Ring || Prototype->Kind == EAbilityPrototypeKind::Field)
        Visual->SetRelativeScale3D(FVector(Prototype->Radius / 100.f, Prototype->Radius / 100.f, .25f));
}

void APureMassRuntime::Impact_Implementation(FVector Position)
{
    if (Prototype && Prototype->ImpactVFX && GetNetMode() != NM_DedicatedServer)
        UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, Prototype->ImpactVFX, Position);
}

void APureMassRuntime::EndPlay(EEndPlayReason::Type Reason)
{
    if (HasAuthority() && IsValid(Surface)) Surface->Destroy();
    Super::EndPlay(Reason);
}

void APureMassRuntime::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(APureMassRuntime, Prototype);
    DOREPLIFETIME(APureMassRuntime, BeamEnd);
    DOREPLIFETIME(APureMassRuntime, WaveRadius);
    DOREPLIFETIME(APureMassRuntime, OrbitBolts);
    DOREPLIFETIME(APureMassRuntime, bFinished);
    DOREPLIFETIME(APureMassRuntime, bSingle);
}
