#pragma once
#include "CoreMinimal.h"
#include "AbilitySystem/Prototypes/AbilityPrototype.h"
#include "ExtensionNode.generated.h"

UENUM(BlueprintType)
enum class EExtensionKind : uint8 { Attach, Stack, Displace, Projectile, Chain, Burst, Delay, Surface };

/** Opt-in graph: old configuration assets are never interpreted as extension nodes. */
UCLASS(BlueprintType)
class TEST_25D_API UExtensionNode : public UAbilityPrototype
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) EExtensionKind Behavior = EExtensionKind::Burst;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UExtensionNode> HitChild;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UExtensionNode> PeriodChild;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UExtensionNode> CompleteChild;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName EffectId;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 MaxTransfers = 2;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float TransferRadius = 350.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 StackThreshold = 3;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float StackLifetime = 4.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float DetonationDelay = .4f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float MoveDistance = 180.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float SafeDistance = 70.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bPull = true;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bSingleTarget = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<TSubclassOf<AActor>> ImmuneActorClasses;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FName> ImmuneActorTags;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TMap<FName, float> ActorTagMovementScale;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<TObjectPtr<class UPureMassMonsterType>> ImmuneMassTypes;
    UFUNCTION(BlueprintPure) bool ValidateGraph() const;
};

UCLASS()
class TEST_25D_API UExtensionCastContext : public UPrototypeCastContext
{
    GENERATED_BODY()
public:
    int32 Surfaces = 0;
    TSet<FName> DetonatedEffects;
};
