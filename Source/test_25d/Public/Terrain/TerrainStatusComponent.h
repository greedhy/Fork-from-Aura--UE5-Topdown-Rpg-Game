#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameplayEffectTypes.h"
#include "Terrain/TerrainSurfaceConfig.h"
#include "TerrainStatusComponent.generated.h"

class ATerrainSurface;
class UAbilitySystemComponent;
class UNiagaraComponent;

USTRUCT()
struct FTerrainStatusPresentation
{
    GENERATED_BODY()
    UPROPERTY() uint8 ActiveMask = 0;
    UPROPERTY() float MovementMultiplier = 1.f;
    UPROPERTY() TArray<TObjectPtr<UNiagaraSystem>> Systems;
};

/** One status owner per creature: merges neighbouring tiles and owns GE cleanup. */
UCLASS(ClassGroup=(Terrain), meta=(BlueprintSpawnableComponent))
class TEST_25D_API UTerrainStatusComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTerrainStatusComponent();
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

    void RefreshContact(ATerrainSurface* Surface);
    UFUNCTION(BlueprintCallable, Category="Terrain") void ClearTerrainEffects();
    UFUNCTION(BlueprintPure, Category="Terrain") bool IsTerrainStatusActive(ETerrainSurfaceType Type) const;
    UFUNCTION(BlueprintPure, Category="Terrain") float GetTerrainMovementMultiplier() const { return Presentation.MovementMultiplier; }

private:
    struct FContact
    {
        TWeakObjectPtr<ATerrainSurface> Surface;
        TWeakObjectPtr<UTerrainSurfaceConfig> Config;
        float Remaining = 0.f;
    };
    TArray<FContact> Contacts;
    FActiveGameplayEffectHandle EffectHandles[4];
    TWeakObjectPtr<UAbilitySystemComponent> EffectASC;
    float RootRemaining = 0.f;
    float RecoveryRemaining = 0.f;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> RootSystem;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> VisualComponents;
    UPROPERTY(ReplicatedUsing=OnRep_Presentation) FTerrainStatusPresentation Presentation;

    UFUNCTION() void OnRep_Presentation();
    void UpdateEffects();
    void UpdatePresentation();
};
