#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "PureMass/PureMassCombatTarget.h"
#include "AbilitySystem/PrototypeExtensions/ExtensionNode.h"
#include "ExtensionRuntime.generated.h"

UCLASS()
class TEST_25D_API AExtensionRuntime : public AActor
{
    GENERATED_BODY()
public:
    AExtensionRuntime();
    static AExtensionRuntime* Spawn(UExtensionCastContext* Context, UExtensionNode* Node, FVector Position,
        FVector Direction, FPureMassCombatTarget Target = {}, int32 Depth = 0, FVector Center = FVector::ZeroVector, bool bConfirmedHit = false);
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(ReplicatedUsing=RefreshVisual, BlueprintReadOnly) TObjectPtr<UExtensionNode> Node;
    UPROPERTY() TObjectPtr<UExtensionCastContext> Context;
    UPROPERTY(Replicated, BlueprintReadOnly) FVector BeamEnd;
    UPROPERTY(Replicated, BlueprintReadOnly) FVector BeamStart;
    UPROPERTY(ReplicatedUsing=RefreshVisual, BlueprintReadOnly) bool bFinished = false;
    bool Hit(FPureMassCombatTarget Candidate, float Scale = 1.f);
    void Finish(bool Cancelled = false);
    FPureMassCombatTarget GetTarget() const { return Target; }
private:
    UPROPERTY() TObjectPtr<class UNiagaraComponent> Visual;
    UPROPERTY() TObjectPtr<class ATerrainSurface> Surface;
    FPureMassCombatTarget Target;
    TSet<FPureMassCombatTarget> HitTargets;
    TArray<FGuid> Moves;
    FVector Direction, Center, LastPosition;
    int32 Depth = 0, Transfers = 0, Hits = 0;
    float Age = 0, Clock = 0, Travel = 0;
    bool bPresented = false;
    bool bConfirmedHit = false;
    bool Emit(UExtensionNode* Child, FVector Position, FPureMassCombatTarget Candidate, FVector EventCenter, bool bFromConfirmedHit = false);
    void ChainStep();
    UFUNCTION() void RefreshVisual();
    UFUNCTION(NetMulticast, Unreliable) void Impact(FVector Position);
};
