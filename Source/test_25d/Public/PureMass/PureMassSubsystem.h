#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "MassEntityTypes.h"
#include "Mass/EntityHandle.h"
#include "MassArchetypeTypes.h"
#include "Mass/MonsterSpatialIndex.h"
#include "PureMass/PureMassTypes.h"
#include "PureMassSubsystem.generated.h"

class UMassEntitySubsystem;
class APawn;
class ATerrainSurface;

UCLASS()
class TEST_25D_API UPureMassSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    UFUNCTION(BlueprintCallable) void Enable();
    UFUNCTION(BlueprintCallable) int32 SpawnMonster(UPureMassMonsterType* Type, FVector Location, FName Room = NAME_None);
    UFUNCTION(BlueprintPure) bool Resolve(int32 Id, FPureMassView& OutView) const;
    UFUNCTION(BlueprintPure) TArray<int32> QueryRadius(FVector Center, float Radius) const;
    int32 Sweep(FVector Start, FVector End, float Radius, float& OutTime, const TSet<int32>* Ignored = nullptr) const;
    UFUNCTION(BlueprintCallable) float ApplyDamage(int32 Id, const FPureMassDamage& Damage);
    UFUNCTION(BlueprintPure) TArray<FPureMassView> GetSnapshots() const;
    void SetClientSnapshots(const TArray<FPureMassView>& Snapshots);
    UFUNCTION(BlueprintPure) bool IsEnabled() const { return bEnabled; }
    bool BeginUpdate(float DeltaSeconds);
    void UpdateMonster(FPureMassFragment& Fragment);
    void FinishUpdate();
    FMassEntityHandle GetEntity(int32 Id) const;
    UFUNCTION(BlueprintPure) int64 GetDeathCount() const { return DeathCount; }
private:
    bool IsAuthority() const;
    void Publish(const FPureMassFragment& Fragment);
    float DamageFragment(FPureMassFragment& Fragment, float Amount, AActor* Source);
    float EvaluateDamage(const FPureMassFragment& Fragment, const FPureMassDamage& Damage) const;
    void AttackPlayer(FPureMassFragment& Fragment, APawn* Player);
    float UpdateTerrain(FPureMassFragment& Fragment);
    void Move(FPureMassFragment& Fragment, FVector Delta);
    UPROPERTY(Transient) TObjectPtr<UMassEntitySubsystem> Mass;
    UPROPERTY(Transient) TArray<TObjectPtr<UPureMassMonsterType>> RetainedTypes;
    UPROPERTY(Transient) TMap<int32, FPureMassView> Views;
    TMap<int32, FMassEntityHandle> Entities;
    FMassArchetypeHandle Archetype;
    FMonsterSpatialIndex Grid;
    TArray<TWeakObjectPtr<APawn>> Players;
    TArray<TWeakObjectPtr<ATerrainSurface>> Terrain;
    TArray<int32> Dead;
    bool bEnabled = false;
    bool bRefreshTerrain = false;
    int64 NextId = 1;
    float DeltaTime = 0.f;
    float NextTerrainScan = 0.f;
    int32 PathsRemaining = 0;
    float LargestRadius = 32.f;
    float LargestHalfHeight = 60.f;
    uint64 DeathCount = 0;
};
