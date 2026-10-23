#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AbilitySystem/Prototypes/AbilityPrototype.h"
#include "PureMassRuntime.generated.h"
class UNiagaraComponent;
class UGameplayAbility;

USTRUCT(BlueprintType)
struct FPureMassOrbitBolt
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FVector Position = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly) bool bLaunched = false;
    UPROPERTY(BlueprintReadOnly) float Age = 0.f;
};

/** One effect actor per active behavior node, never an actor per enemy. */
UCLASS()
class TEST_25D_API APureMassRuntime : public AActor
{
    GENERATED_BODY()
public:
    APureMassRuntime();
    static APureMassRuntime* Spawn(UPrototypeCastContext* Context, UAbilityPrototype* Config,
        FVector Position, FVector Direction, int32 TargetId = INDEX_NONE, int32 Depth = 0, bool bSingle = false);
    static void NotifyCommittedAttack(AActor* Caster, UGameplayAbility* Ability, int32 TargetId);
    static bool EntityBeforeWall(float EntityTime, bool bWall, float WallTime) { return FMath::IsFinite(EntityTime) && EntityTime >= 0.f && EntityTime <= 1.f && (!bWall || EntityTime < WallTime); }
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UFUNCTION(BlueprintCallable) void CancelCast();
    bool IsFinished() const { return bFinished; }
    UPROPERTY(ReplicatedUsing=RefreshVisual, BlueprintReadOnly) TObjectPtr<UAbilityPrototype> Prototype;
    UPROPERTY() TObjectPtr<UPrototypeCastContext> Context;
    UPROPERTY(Replicated, BlueprintReadOnly) FVector BeamEnd = FVector::ZeroVector;
    UPROPERTY(Replicated) float WaveRadius = 0.f;
    UPROPERTY(Replicated, BlueprintReadOnly) TArray<FPureMassOrbitBolt> OrbitBolts;
private:
    UPROPERTY() TObjectPtr<UNiagaraComponent> Visual;
    UPROPERTY() TArray<TObjectPtr<UNiagaraComponent>> BoltVisuals;
    UPROPERTY() TObjectPtr<ATerrainSurface> Surface;
    UPROPERTY(ReplicatedUsing=RefreshVisual) bool bFinished = false;
    UPROPERTY(Replicated) bool bSingle = false;
    bool bReturning = false, bPresented = false;
    FVector Direction = FVector::ForwardVector;
    FVector ChainOrigin = FVector::ZeroVector;
    int32 TargetId = INDEX_NONE, Depth = 0, Emissions = 0;
    TSet<int32> HitIds;
    float Age = 0.f, PeriodClock = 0.f, Travel = 0.f, LaunchClock = 0.f;
    UFUNCTION() void RefreshVisual();
    UFUNCTION(NetMulticast, Unreliable) void Impact(FVector Position);
    bool Visible(FVector Origin, FVector Point) const;
    bool Hit(int32 Id, float Scale = 1.f);
    bool Emit(UAbilityPrototype* Child, FVector Position, int32 Id);
    void Pulse();
    void Projectile(float Delta);
    void Chain();
    void Orbit(float Delta);
    int32 Nearest(FVector Origin, float Radius) const;
    void Finish(bool bCancelled);
};
