#pragma once

#include "CoreMinimal.h"

class UWorld;
class AActor;

/** A cast-local reference. Mass IDs and weak Actor identities never share a namespace.
 * Network requests use SingleTargetHit: Actor + INDEX_NONE, or no Actor + Mass ID.
 */
struct TEST_25D_API FPureMassCombatTarget
{
    int32 EntityId = INDEX_NONE;
    TWeakObjectPtr<AActor> Actor;

    FPureMassCombatTarget() = default;
    FPureMassCombatTarget(int32 InEntityId) : EntityId(InEntityId) {}
    static FPureMassCombatTarget FromActor(AActor* InActor)
    {
        FPureMassCombatTarget Result;
        Result.Actor = InActor;
        return Result;
    }
    bool IsActor() const { return !Actor.IsExplicitlyNull(); }
    bool IsSet() const { return IsActor() || EntityId > 0; }
    bool operator==(const FPureMassCombatTarget& Other) const { return EntityId == Other.EntityId && Actor == Other.Actor; }
    bool operator!=(const FPureMassCombatTarget& Other) const { return !(*this == Other); }
    friend uint32 GetTypeHash(const FPureMassCombatTarget& Target)
    {
        return HashCombine(::GetTypeHash(Target.EntityId), ::GetTypeHash(Target.Actor));
    }
};

/** Shared filtering, geometry and lookup for player abilities against both enemy representations. */
namespace PureMassCombat
{
    TEST_25D_API bool Resolve(UWorld* World, AActor* Caster, const FPureMassCombatTarget& Target, FVector& OutLocation);
    TEST_25D_API TArray<FPureMassCombatTarget> Gather(UWorld* World, AActor* Caster, FVector Origin, float Radius);
    TEST_25D_API bool Visible(UWorld* World, AActor* Caster, FVector Origin, const FPureMassCombatTarget& Target, AActor* IgnoredEffect = nullptr);
    TEST_25D_API bool GroundVisible(UWorld* World, AActor* Caster, FVector Origin, FVector Point);
    /** Returns the earliest hostile hit only when strictly before world obstruction. Allies are transparent. */
    TEST_25D_API FPureMassCombatTarget Sweep(UWorld* World, AActor* Caster, FVector Start, FVector End,
        float Radius, float& OutTime, FHitResult& OutWall, const TSet<FPureMassCombatTarget>* Ignored = nullptr, AActor* IgnoredEffect = nullptr);
}
