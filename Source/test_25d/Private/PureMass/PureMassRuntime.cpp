#include "PureMass/PureMassRuntime.h"
#include "PureMass/PureMassAbility.h"
#include "PureMass/PureMassSubsystem.h"
#include "AbilitySystem/Prototypes/PrototypeRuntime.h"
#include "AbilitySystem/Data/OrbitingFireBoltConfig.h"
#include "AbilitySystem/Ability/MyDamageGameplayAbility.h"
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
    FVector Position, FVector InDirection, int32 Id, int32 InDepth, bool bInSingle)
{
    AActor* Caster = InContext ? InContext->Caster.Get() : nullptr;
    if (!IsValid(Caster) || !Caster->HasAuthority() || !Config || !Config->IsValidConfiguration()
        || Position.ContainsNaN() || InDirection.ContainsNaN()) return nullptr;
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
    R->TargetId = Id;
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

bool APureMassRuntime::Visible(FVector Origin, FVector Point) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PureMassLOS), false, GetOwner());
    Query.AddIgnoredActor(this);
    FHitResult Wall;
    return !GetWorld()->LineTraceSingleByChannel(Wall, Origin, Point, ECC_Visibility, Query);
}

bool APureMassRuntime::Hit(int32 Id, float Scale)
{
    if (!HasAuthority() || !Context || Context->bCancelled || bFinished) return false;
    auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
    FPureMassView View;
    if (!Mass || !Mass->Resolve(Id, View)) return false;
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
    Mass->ApplyDamage(Id, Damage);
    Impact(View.Location);
    Emit(Prototype->OnHit, View.Location, Id);
    return true;
}

bool APureMassRuntime::Emit(UAbilityPrototype* Child, FVector Position, int32 Id)
{
    return HasAuthority() && Context && !Context->bCancelled && Child
        && Spawn(Context, Child, Position, Direction, Id, Depth + 1) != nullptr;
}

int32 APureMassRuntime::Nearest(FVector Origin, float Radius) const
{
    auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
    if (!Mass) return INDEX_NONE;
    float Best = FMath::Square(Radius);
    int32 Result = INDEX_NONE;
    for (int32 Id : Mass->QueryRadius(Origin, Radius))
    {
        FPureMassView V;
        if (HitIds.Contains(Id) || !Mass->Resolve(Id, V)) continue;
        const float Dist = FVector::DistSquared(Origin, V.Location);
        if (Dist <= Best && Visible(Origin, V.Location)) { Result = Id; Best = Dist; }
    }
    return Result;
}

void APureMassRuntime::Pulse()
{
    auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
    if (!Mass) return;
    using K = EAbilityPrototypeKind;
    const auto Kind = Prototype->Kind;
    const FVector Facing = Direction.GetSafeNormal2D(SMALL_NUMBER, FVector::ForwardVector);
    const FVector Right = FVector::CrossProduct(FVector::UpVector, Facing);
    const float Bounds = Kind == K::Line ? FMath::Sqrt(FMath::Square(Prototype->Range) + FMath::Square(Prototype->Width*.5f) + FMath::Square(Prototype->ShapeHalfHeight))
        : Kind == K::Ring ? FMath::Sqrt(FMath::Square(Prototype->Radius) + FMath::Square(Prototype->ShapeHalfHeight)) : Prototype->Radius;
    for (int32 Id : Mass->QueryRadius(GetActorLocation(), Bounds))
    {
        FPureMassView V;
        if (!Mass->Resolve(Id, V)) continue;
        const FVector Offset = V.Location - GetActorLocation();
        if (Kind == K::Cone && !Offset.IsNearlyZero()
            && FVector::DotProduct(Facing, Offset.GetSafeNormal2D()) < FMath::Cos(FMath::DegreesToRadians(Prototype->SpreadDegrees * .5f))) continue;
        if ((Kind == K::Line || Kind == K::Ring) && FMath::Abs(Offset.Z) > Prototype->ShapeHalfHeight) continue;
        if (Kind == K::Ring && (Offset.SizeSquared2D() < FMath::Square(Prototype->InnerRadius) || Offset.SizeSquared2D() > FMath::Square(Prototype->Radius))) continue;
        if (Kind == K::Line)
        {
            const float Along = FVector::DotProduct(Facing, Offset);
            if (Along < 0.f || Along > Prototype->Range || FMath::Abs(FVector::DotProduct(Right, Offset)) > Prototype->Width * .5f) continue;
        }
        if (Kind == K::Wave && (HitIds.Contains(Id) || Offset.SizeSquared() > FMath::Square(WaveRadius))) continue;
        if (!Visible(GetActorLocation(), V.Location)) continue;
        Hit(Id);
        if (Kind == K::Wave) HitIds.Add(Id);
    }
}

void APureMassRuntime::Projectile(float Delta)
{
    auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
    if (!Mass) { Finish(true); return; }
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
        FPureMassView V;
        if (!Mass->Resolve(TargetId, V)) { Finish(false); return; }
        Direction = FMath::VInterpNormalRotationTo(Direction, (V.Location - GetActorLocation()).GetSafeNormal(), Delta, Prototype->HomingTurnRate);
    }
    const float Step = FMath::Min(Prototype->Speed * Delta, Remaining);
    const FVector Start = GetActorLocation(), End = Start + Direction * Step;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PureMassProjectile), false, GetOwner());
    Query.AddIgnoredActor(this);
    FHitResult Wall;
    const bool bWall = GetWorld()->SweepSingleByChannel(Wall, Start, End, FQuat::Identity, ECC_Visibility,
        FCollisionShape::MakeSphere(Prototype->CollisionRadius), Query);
    // Re-query with the growing exclusion set: one entity can never absorb a second hit in this pass.
    for (int32 I = 0; I < 64; ++I)
    {
        float Time = 1.f;
        const int32 Id = Mass->Sweep(Start, End, Prototype->CollisionRadius, Time, &HitIds);
        if (Id == INDEX_NONE || !EntityBeforeWall(Time, bWall, Wall.Time)) break;
        if (bReturn && HitIds.Num() >= Prototype->Count) break;
        SetActorLocation(FMath::Lerp(Start, End, Time));
        Hit(Id, bReturn ? (bReturning ? Prototype->DamageFalloff : 1.f) : FMath::Pow(Prototype->DamageFalloff, HitIds.Num()));
        HitIds.Add(Id);
        if (!bReturn && (Prototype->Kind != K::Piercing || HitIds.Num() >= Prototype->Count)) { Finish(false); return; }
    }
    if (bWall) { SetActorLocation(Wall.Location); Impact(Wall.ImpactPoint); Finish(false); return; }
    SetActorLocation(End);
    SetActorRotation(Direction.Rotation());
    Travel += Step;
    if (bReturn)
    {
        if (bReturning && Step >= Remaining) { Finish(false); return; }
        if (!bReturning && Travel >= Prototype->Range)
        {
            bReturning = true;
            HitIds.Reset();
            const float Remainder = Delta - Step / Prototype->Speed;
            if (Remainder > SMALL_NUMBER) Projectile(Remainder);
        }
    }
    else if (Travel >= Prototype->Range) Finish(false);
}

void APureMassRuntime::Chain()
{
    auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
    FPureMassView V;
    const float Reach = HitIds.IsEmpty() ? Prototype->Range : Prototype->Radius;
    if (!Mass || HitIds.Num() >= Prototype->Count || HitIds.Contains(TargetId) || !Mass->Resolve(TargetId, V)
        || FVector::DistSquared(ChainOrigin, V.Location) > FMath::Square(Reach) || !Visible(ChainOrigin, V.Location))
    { Finish(false); return; }
    SetActorLocation(ChainOrigin);
    BeamEnd = V.Location;
    Hit(TargetId, FMath::Pow(Prototype->DamageFalloff, HitIds.Num()));
    HitIds.Add(TargetId);
    ChainOrigin = V.Location;
    TargetId = Nearest(V.Location, Prototype->Radius);
    ForceNetUpdate();
    if (TargetId == INDEX_NONE || HitIds.Num() >= Prototype->Count) Finish(false);
}

void APureMassRuntime::NotifyCommittedAttack(AActor* Caster, UGameplayAbility* Ability, int32 Id)
{
    auto* DamageAbility = Cast<UMyDamageGameplayAbility>(Ability);
    if (!IsValid(Caster) || !Caster->HasAuthority() || !DamageAbility || !DamageAbility->HasCommittedOffensiveAttack()) return;
    auto* Mass = Caster->GetWorld()->GetSubsystem<UPureMassSubsystem>();
    FPureMassView V;
    if (!Mass || !Mass->Resolve(Id, V)) return;
    for (TActorIterator<APureMassRuntime> It(Caster->GetWorld()); It; ++It)
        if (It->GetOwner() == Caster && !It->bFinished && It->Prototype && It->Prototype->Kind == EAbilityPrototypeKind::Orbit
            && It->Prototype->OrbitSettings && FVector::DistSquared(Caster->GetActorLocation(), V.Location) <= FMath::Square(It->Prototype->OrbitSettings->MaxTargetDistance))
            It->TargetId = Id;
}

void APureMassRuntime::Orbit(float Delta)
{
    const auto* Settings = Prototype->OrbitSettings.Get();
    auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
    if (!Settings || !Mass) { Finish(true); return; }
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
        Emit(Prototype->OnPeriod, GetActorLocation(), TargetId);
    }
    FPureMassView Target;
    const bool bTarget = Mass->Resolve(TargetId, Target)
        && FVector::DistSquared(GetActorLocation(), Target.Location) <= FMath::Square(Settings->MaxTargetDistance);
    if (!bTarget) TargetId = INDEX_NONE;
    if (bTarget && LaunchClock >= Settings->LaunchInterval && Visible(GetActorLocation(), Target.Location))
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
        const FVector End = FMath::VInterpConstantTo(Start, Target.Location, Delta, Settings->ProjectileSpeed);
        float Time = 1.f;
        const int32 Id = Mass->Sweep(Start, End, Prototype->CollisionRadius, Time);
        FHitResult Wall;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(PureMassOrbit), false, GetOwner()); Query.AddIgnoredActor(this);
        const bool bWall = GetWorld()->SweepSingleByChannel(Wall, Start, End, FQuat::Identity, ECC_Visibility,
            FCollisionShape::MakeSphere(Prototype->CollisionRadius), Query);
        if (Id != INDEX_NONE && EntityBeforeWall(Time, bWall, Wall.Time)) { Hit(Id); OrbitBolts.RemoveAt(I); continue; }
        if (bWall || Bolt.Age >= Settings->MaxFlightSeconds) { OrbitBolts.RemoveAt(I); continue; }
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
            if (Kind != K::Burst) Emit(Prototype->OnPeriod, GetActorLocation(), TargetId);
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
        if (Age >= Prototype->ArmDelay && Nearest(GetActorLocation(), Prototype->Radius) != INDEX_NONE) { Pulse(); Finish(false); }
        return;
    }
    auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
    if (Kind == K::Beam)
    {
        FPureMassView V;
        if (!Mass || !Mass->Resolve(TargetId, V) || FVector::DistSquared(GetOwner()->GetActorLocation(), V.Location) > FMath::Square(Prototype->Range)
            || !Visible(GetOwner()->GetActorLocation() + FVector(0,0,30), V.Location)) { Finish(false); return; }
        SetActorLocation(GetOwner()->GetActorLocation() + FVector(0,0,30));
        BeamEnd = V.Location;
    }
    if (Kind == K::Beam || Kind == K::Field || Kind == K::Chain || Kind == K::Emitter) PeriodClock += Delta;
    if (Kind == K::Chain && HitIds.IsEmpty()) { Chain(); PeriodClock = 0.f; return; }
    // At most eight catch-up pulses per frame; no unbounded bursts after a hitch.
    for (int32 I = 0; I < 8 && !bFinished && PeriodClock >= Prototype->Period; ++I)
    {
        PeriodClock -= Prototype->Period;
        if (Kind == K::Chain) { Chain(); continue; }
        if (Kind == K::Field) Pulse();
        if (Kind == K::Beam) Hit(TargetId);
        if (Kind == K::Emitter)
        {
            TargetId = Nearest(GetActorLocation(), Prototype->Radius);
            FPureMassView V;
            if (TargetId == INDEX_NONE || !Mass || !Mass->Resolve(TargetId, V)) { PeriodClock = 0.f; break; }
            Direction = (V.Location - GetActorLocation()).GetSafeNormal(SMALL_NUMBER, Direction);
            if (Emit(Prototype->OnPeriod, GetActorLocation(), TargetId) && ++Emissions >= Prototype->Count) Finish(false);
        }
        else Emit(Prototype->OnPeriod, GetActorLocation(), TargetId);
    }
}

void APureMassRuntime::Finish(bool bCancelled)
{
    if (bFinished) return;
    bFinished = true;
    if (bCancelled) { if (Context) Context->bCancelled = true; }
    else Emit(Prototype->OnExpire, Prototype->Kind == EAbilityPrototypeKind::Chain ? ChainOrigin : GetActorLocation(), TargetId);
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
