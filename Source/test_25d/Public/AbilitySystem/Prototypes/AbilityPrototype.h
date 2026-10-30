#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameplayTagContainer.h"
#include "MyAbilityTypes.h"
#include "AbilityPrototype.generated.h"

class UNiagaraSystem;
class UOrbitingFireBoltConfig;
class ATerrainSurface;

UENUM(BlueprintType)
enum class EAbilityPrototypeKind : uint8 { Projectile, Multishot, Burst, Beam, Surface, Orbit, Field, Trap, Homing, Piercing, Chain, Cone, Wave, Returning, Emitter, Delay, Ring, Line };

/** A reusable behavior node. Child nodes share the caster, level and a bounded cast budget. */
UCLASS(BlueprintType)
class TEST_25D_API UAbilityPrototype : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly) EAbilityPrototypeKind Kind = EAbilityPrototypeKind::Projectile;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText DisplayName;
    /** Designer notes. Menu numbers are generated from the current numeric configuration. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FText Summary;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FGameplayTag CooldownTag;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float ManaCost = 10.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float ManaPerSecond = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float Cooldown = 2.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Range = 1200.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Radius = 250.f;
    /** Ring excludes the area closer than this horizontal radius. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float InnerRadius = 100.f;
    /** Full horizontal width of a Line; its forward length uses Range. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Width = 140.f;
    /** Ring and Line reject target centres on other floors. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float ShapeHalfHeight = 120.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1", ClampMax="60")) float Duration = 6.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.1")) float Period = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float Damage = 25.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float DamagePerLevel = 5.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FGameplayTag DamageType;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1", ClampMax="16")) int32 Count = 3;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0", ClampMax="360")) float SpreadDegrees = 45.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float Speed = 900.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1")) float CollisionRadius = 12.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float ArmDelay = .75f;
    /** Maximum homing turn speed in degrees per second. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="1", ClampMax="720")) float HomingTurnRate = 360.f;
    /** Damage multiplier per additional piercing/chain target. Count caps unique targets. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0", ClampMax="1")) float DamageFalloff = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bTargetSelf = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UNiagaraSystem> LoopVFX;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UNiagaraSystem> ImpactVFX;
    /** Presentation only: never changes gameplay origin or damage volume. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") FVector LoopVFXScale = FVector::OneVector;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") FVector ImpactVFXScale = FVector::OneVector;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Presentation") bool bGroundPresentation = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TSubclassOf<ATerrainSurface> SurfaceClass;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UOrbitingFireBoltConfig> OrbitSettings;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Composition") TObjectPtr<UAbilityPrototype> OnHit;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Composition") TObjectPtr<UAbilityPrototype> OnPeriod;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Composition") TObjectPtr<UAbilityPrototype> OnExpire;
    UFUNCTION(BlueprintPure) bool IsValidConfiguration() const;
    float DamageAtLevel(int32 Level) const;
};

/** Server-only shared context; never use client-supplied damage or child-node parameters. */
UCLASS()
class TEST_25D_API UPrototypeCastContext : public UObject
{
    GENERATED_BODY()
public:
    UPROPERTY() FDamageEffectParams DamageParams;
    UPROPERTY() TWeakObjectPtr<AActor> Caster;
    UPROPERTY(BlueprintReadOnly) FGuid CastId;
    UPROPERTY(BlueprintReadOnly) int32 Level = 1;
    int32 Spawned = 0;
    bool bCancelled = false;
    bool ReserveSpawn(int32 Depth);
};
