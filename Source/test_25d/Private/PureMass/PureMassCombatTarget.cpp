#include "PureMass/PureMassCombatTarget.h"
#include "PureMass/PureMassSubsystem.h"
#include "AbilitySystem/Prototypes/PrototypeRuntime.h"
#include "Interface/CombatInterface.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "test_25d/test_25d.h"

namespace
{
bool CanTargetMass(AActor* Caster)
{
    // Current Mass population is the enemy faction. Actor enemies must not damage allies.
    return IsValid(Caster) && !Caster->ActorHasTag(TEXT("Enemy"));
}

void IgnoreCombatActors(UWorld* World, FCollisionQueryParams& Query)
{
    // Combatants are tested separately from world obstruction, exactly like non-colliding Mass instances.
    // This also prevents friendly characters and corpses from becoming projectile walls.
    for (TActorIterator<AActor> It(World); It; ++It)
        if (It->Implements<UCombatInterface>()) Query.AddIgnoredActor(*It);
}

FCollisionResponseParams ObstructionResponses()
{
    FCollisionResponseParams Responses;
    Responses.CollisionResponse.SetResponse(ECC_Projectile, ECR_Ignore);
    return Responses;
}
}

bool PureMassCombat::Resolve(UWorld* World, AActor* Caster, const FPureMassCombatTarget& Target, FVector& OutLocation)
{
    OutLocation = FVector::ZeroVector;
    if (!World || !IsValid(Caster) || Caster->GetWorld() != World) return false;
    if (Target.IsActor())
    {
        AActor* Actor = Target.Actor.Get();
        if (Target.EntityId != INDEX_NONE || !IsValid(Actor) || Actor->GetWorld() != World
            || !APrototypeRuntime::IsEnemy(Caster, Actor)) return false;
        OutLocation = Actor->GetActorLocation();
        return !OutLocation.ContainsNaN();
    }
    if (Target.EntityId <= 0 || !CanTargetMass(Caster)) return false;
    auto* Mass = World->GetSubsystem<UPureMassSubsystem>();
    FPureMassView View;
    if (!Mass || !Mass->Resolve(Target.EntityId, View) || View.Health <= 0.f || View.State == 3) return false;
    OutLocation = View.Location;
    return !OutLocation.ContainsNaN();
}

TArray<FPureMassCombatTarget> PureMassCombat::Gather(UWorld* World, AActor* Caster, FVector Origin, float Radius)
{
    TArray<FPureMassCombatTarget> Result;
    if (!World || !IsValid(Caster) || Caster->GetWorld() != World || Origin.ContainsNaN()
        || !FMath::IsFinite(Radius) || Radius < 0.f) return Result;
    if (CanTargetMass(Caster))
        if (auto* Mass = World->GetSubsystem<UPureMassSubsystem>())
            for (int32 Id : Mass->QueryRadius(Origin, Radius)) Result.Emplace(Id);
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (!It->Implements<UCombatInterface>()) continue;
        const auto Target = FPureMassCombatTarget::FromActor(*It);
        FVector Location;
        if (Resolve(World, Caster, Target, Location) && FVector::DistSquared(Origin, Location) <= FMath::Square(Radius))
            Result.Add(Target);
    }
    return Result;
}

bool PureMassCombat::Visible(UWorld* World, AActor* Caster, FVector Origin, const FPureMassCombatTarget& Target, AActor* IgnoredEffect)
{
    FVector Location;
    if (Origin.ContainsNaN() || !Resolve(World, Caster, Target, Location)) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MixedCombatLOS), false, Caster);
    if (IgnoredEffect) Query.AddIgnoredActor(IgnoredEffect);
    IgnoreCombatActors(World, Query);
    FHitResult Wall;
    return !World->LineTraceSingleByChannel(Wall, Origin, Location, ECC_Visibility, Query, ObstructionResponses());
}

bool PureMassCombat::GroundVisible(UWorld* World, AActor* Caster, FVector Origin, FVector Point)
{
    if (!World || !IsValid(Caster) || Caster->GetWorld() != World || Origin.ContainsNaN() || Point.ContainsNaN()) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MixedGroundLOS), false, Caster);
    IgnoreCombatActors(World, Query);
    FHitResult Wall;
    return !World->LineTraceSingleByChannel(Wall, Origin, Point, ECC_Visibility, Query, ObstructionResponses())
        || FVector::DistSquared(Wall.ImpactPoint, Point) <= FMath::Square(15.f);
}

FPureMassCombatTarget PureMassCombat::Sweep(UWorld* World, AActor* Caster, FVector Start, FVector End,
    float Radius, float& OutTime, FHitResult& OutWall, const TSet<FPureMassCombatTarget>* Ignored, AActor* IgnoredEffect)
{
    OutTime = 1.f;
    OutWall = FHitResult();
    FPureMassCombatTarget Best;
    if (!World || !IsValid(Caster) || Caster->GetWorld() != World || Start.ContainsNaN() || End.ContainsNaN()
        || !FMath::IsFinite(Radius) || Radius < 0.f) return Best;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MixedCombatSweep), false, Caster);
    if (IgnoredEffect) Query.AddIgnoredActor(IgnoredEffect);
    IgnoreCombatActors(World, Query);
    const bool bWall = Radius > 0.f
        ? World->SweepSingleByChannel(OutWall, Start, End, FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(Radius), Query, ObstructionResponses())
        : World->LineTraceSingleByChannel(OutWall, Start, End, ECC_Visibility, Query, ObstructionResponses());
    if (CanTargetMass(Caster))
        if (auto* Mass = World->GetSubsystem<UPureMassSubsystem>())
        {
            TSet<int32> IgnoredEntities;
            if (Ignored) for (const auto& Target : *Ignored) if (!Target.IsActor()) IgnoredEntities.Add(Target.EntityId);
            float Time = 1.f;
            const int32 Id = Mass->Sweep(Start, End, Radius, Time, &IgnoredEntities);
            if (Id > 0 && (!bWall || Time < OutWall.Time)) { Best = Id; OutTime = Time; }
        }
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        if (!It->Implements<UCombatInterface>()) continue;
        const auto Target = FPureMassCombatTarget::FromActor(*It);
        FVector Location;
        if ((Ignored && Ignored->Contains(Target)) || !Resolve(World, Caster, Target, Location)) continue;
        float ActorRadius = 0.f, HalfHeight = 0.f;
        It->GetSimpleCollisionCylinder(ActorRadius, HalfHeight);
        if (!FMath::IsFinite(ActorRadius) || !FMath::IsFinite(HalfHeight) || ActorRadius <= 0.f) continue;
        float Time = 1.f;
        if (PureMassGeometry::SweepCapsule(Start, End, Radius, Location, ActorRadius, FMath::Max(ActorRadius, HalfHeight), Time)
            && (!bWall || Time < OutWall.Time) && (!Best.IsSet() || Time < OutTime))
        { Best = Target; OutTime = Time; }
    }
    return Best;
}
