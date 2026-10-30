#pragma once
#include "CoreMinimal.h"
#include "Character/EnemyCharacter.h"

/** Floor-local ownership ledger. Actors remain owned by the World, never the GameInstance. */
struct FDungeonEnemyPool
{
    struct FEntry
    {
        TWeakObjectPtr<AEnemyCharacter> Actor;
        FName LastRoom;
        bool Idle = false;
    };
    TArray<FEntry> Entries;
    int32 CountClass(UClass* Class) const
    {
        return Entries.FilterByPredicate([Class](const FEntry& E)
            { return E.Actor.IsValid() && !E.Actor->IsActorBeingDestroyed() && E.Actor->GetClass()==Class; }).Num();
    }
    void Prune() { Entries.RemoveAll([](const FEntry& E) { return !E.Actor.IsValid() || E.Actor->IsActorBeingDestroyed(); }); }
    bool Adopt(AEnemyCharacter* Actor, FName Room, int32 Capacity)
    {
        Prune();
        if (!IsValid(Actor) || Entries.Num() >= FMath::Clamp(Capacity, 0, 64)
            || Entries.ContainsByPredicate([&](const FEntry& E) { return E.Actor == Actor; })) return false;
        Entries.Add({Actor, Room, false});
        return true;
    }
    AEnemyCharacter* Acquire(UClass* Class, FName Room)
    {
        Prune();
        for (auto& E : Entries)
            if (E.Idle && E.LastRoom != Room && E.Actor->GetClass() == Class)
            { E.Idle = false; E.LastRoom = Room; return E.Actor.Get(); }
        return nullptr;
    }
    bool Retire(AEnemyCharacter* Actor)
    {
        for (auto& E : Entries) if (E.Actor == Actor && !E.Idle) { E.Idle = true; return true; }
        return false;
    }
    int32 IdleCount() const
    {
        return Entries.FilterByPredicate([](const FEntry& E) { return E.Idle && E.Actor.IsValid(); }).Num();
    }
};
