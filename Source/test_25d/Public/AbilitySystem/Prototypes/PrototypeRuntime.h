#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AbilitySystem/Prototypes/AbilityPrototype.h"
#include "PrototypeRuntime.generated.h"

class UNiagaraComponent;
class AMyOrbitingFireBolt;
class UGameplayAbility;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FPrototypeEvent, FName, Event, AActor*, Target, FVector, Location);

/** Replicated presentation with authority-only gameplay. Each cast owns an independent context. */
UCLASS()
class TEST_25D_API APrototypeRuntime : public AActor
{
    GENERATED_BODY()
public:
    APrototypeRuntime();
    static APrototypeRuntime* Spawn(UPrototypeCastContext* Context, UAbilityPrototype* Config,
        const FVector& Position, const FVector& Direction, AActor* Target, int32 Depth = 0, bool bSingle = false);
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(ReplicatedUsing=OnRep_Prototype, BlueprintReadOnly) TObjectPtr<UAbilityPrototype> Prototype;
    UPROPERTY(Replicated, BlueprintReadOnly) FVector BeamEnd;
    UPROPERTY(Replicated, BlueprintReadOnly) float WaveRadius = 0.f;
    UPROPERTY(Replicated, BlueprintReadOnly) bool bReturning = false;
    UPROPERTY(BlueprintAssignable) FPrototypeEvent BehaviorEvent;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<UPrototypeCastContext> Context;
    UFUNCTION(BlueprintPure) int32 GetOrbitCount() const;
    UFUNCTION(BlueprintPure) bool IsFinished() const { return bFinished; }
    UFUNCTION(BlueprintCallable) void CancelCast();
    static bool IsEnemy(AActor* Caster, AActor* Target);
    static bool SpendMana(AActor* Caster, float Amount);
    static bool ProjectSurfaceToGround(AActor* Caster, const FVector& Position, FVector& OutPosition);
    void GatherTargets(TArray<AActor*>& Out) const;
private:
    UPROPERTY() TObjectPtr<UNiagaraComponent> Visual;
    UPROPERTY() TObjectPtr<UNiagaraComponent> InnerVisual;
    UPROPERTY() TObjectPtr<ATerrainSurface> Surface;
    UPROPERTY() TArray<TObjectPtr<AMyOrbitingFireBolt>> Bolts;
    TWeakObjectPtr<AActor> AttackTarget;
    TWeakObjectPtr<AActor> LastChainTarget;
    TSet<TWeakObjectPtr<AActor>> HitTargets;
    FVector ChainOrigin = FVector::ZeroVector;
    FVector Direction = FVector::ForwardVector;
    float Age = 0.f, PeriodClock = 0.f, ManaClock = 0.f, LaunchClock = 0.f, Distance = 0.f;
    int32 Depth = 0;
    int32 Emissions = 0;
    UPROPERTY(Replicated) bool bSingleProjectile = false;
    UPROPERTY(ReplicatedUsing=OnRep_Finished) bool bFinished = false;
    UPROPERTY(Replicated) bool bImpactOnFinish = false;
    bool bPresentationReady = false, bFinishPresented = false;
    FDelegateHandle AttackDelegate;
    UFUNCTION() void OnRep_Prototype();
    UFUNCTION() void OnRep_Finished();
    UFUNCTION(NetMulticast, Unreliable) void MulticastImpact(FVector Position);
    bool Emit(FName Event, UAbilityPrototype* Child, AActor* Target, FVector Position);
    void Hit(AActor* Target, float Scale = 1.f);
    void Pulse();
    void Finish(bool bCancelled);
    void TickProjectile(float Delta);
    void TickChain(float Delta);
    void ConePulse();
    void ShapePulse();
    void TickWave(float Delta);
    void TickEmitter(float Delta);
    bool VisibleFrom(const FVector& Origin, AActor* Target) const;
    void TickOrbit(float Delta);
    void OffensiveAttack(UGameplayAbility* Ability, AActor* Target);
    void OrbitHit(AActor* Target);
    bool HasLineOfSight(AActor* Target) const;
    void CleanupOwnedActors();
};
