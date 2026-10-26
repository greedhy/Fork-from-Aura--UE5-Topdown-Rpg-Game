#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "AbilitySystem/PrototypeExtensions/ExtensionNode.h"
#include "PureMass/PureMassCombatTarget.h"
#include "ExtensionWorldSubsystem.generated.h"

USTRUCT()
struct FExtensionStackState
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UExtensionCastContext> Context;
    UPROPERTY() TObjectPtr<UExtensionNode> Node;
    FPureMassCombatTarget Target;
    FVector Position, Direction;
    int32 Depth = 0, Layers = 0, VisualId = 0;
    float Remaining = 0;
    bool bPending = false;
};

USTRUCT()
struct FExtensionMoveState
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UExtensionCastContext> Context;
    UPROPERTY() TObjectPtr<UExtensionNode> Node;
    FPureMassCombatTarget Target;
    FGuid Token;
    FVector Destination;
    float Remaining = 0;
    uint16 RootMotionId = 0;
};

UCLASS()
class TEST_25D_API UExtensionWorldSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
    virtual TStatId GetStatId() const override;
    virtual void Tick(float Delta) override;
    virtual void Deinitialize() override;
    /** Explicitly cancel persistent effects after their initiating GA has ended. Authority only. */
    UFUNCTION(BlueprintCallable) void CancelCasterEffects(AActor* Caster);
    bool AddStack(UExtensionCastContext* Context, UExtensionNode* Node, FPureMassCombatTarget Target,
        FVector Position, FVector Direction, int32 Depth, bool bConfirmedHit = false);
    FGuid RequestDisplacement(UExtensionCastContext* Context, UExtensionNode* Node, FPureMassCombatTarget Target, FVector Center, FVector Direction);
    void MoveMass(struct FPureMassFragment& Fragment, float Delta);
    bool WasMoveReplaced(FGuid Token) const { return Replaced.Contains(Token); }
    int32 StackCount() const { return Stacks.Num(); }
    int32 LayersFor(AActor* Caster, FName EffectId, FPureMassCombatTarget Target) const;
    static bool CasterAlive(const UPrototypeCastContext* Context);
    static bool ConstrainMove(UWorld* World, AActor* Ignore, FVector Start, FVector Desired, float Radius, float HalfHeight, FVector& Result);
private:
    UPROPERTY() TArray<FExtensionStackState> Stacks;
    UPROPERTY() TArray<FExtensionMoveState> Moves;
    UPROPERTY() TObjectPtr<class AExtensionPresentation> Presentation;
    TMap<FGuid, float> Replaced;
    int32 NextVisualId = 1;
};
