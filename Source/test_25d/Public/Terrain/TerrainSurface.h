#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TerrainSurfaceConfig.h"
#include "TerrainSurface.generated.h"

class ABaseCharacter;
class UBoxComponent;
class UStaticMeshComponent;
class UNiagaraComponent;

/** Place this actor instead of a cosmetic-only mesh to enable terrain gameplay. */
UCLASS()
class TEST_25D_API ATerrainSurface : public AActor
{
    GENERATED_BODY()
public:
    ATerrainSurface();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Terrain") TObjectPtr<UTerrainSurfaceConfig> Config;
    UPROPERTY(ReplicatedUsing=OnRep_SurfaceSize, EditAnywhere, BlueprintReadOnly, Category="Terrain", meta=(ClampMin="50")) FVector2D SurfaceSize = FVector2D(400.f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Terrain", meta=(ClampMin="2")) float ContactHeight = 20.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Terrain") bool bAffectPlayers = true;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Terrain") bool bAffectEnemies = true;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Terrain") bool bRequireGrounded = true;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Terrain") bool bEnabled = true;
    // World terrain keeps its existing rules. Skill-created surfaces filter against their caster.
    UPROPERTY(Replicated, EditAnywhere, BlueprintReadOnly, Category="Terrain") bool bOnlyAffectCasterEnemies = false;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Terrain") TObjectPtr<UBoxComponent> Area;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Terrain") TObjectPtr<UStaticMeshComponent> Ground;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Terrain") TObjectPtr<UNiagaraComponent> SurfaceParticles;

    UFUNCTION(BlueprintPure, Category="Terrain") bool CanAffectCharacter(ABaseCharacter* Character) const;
    UFUNCTION(BlueprintCallable, Category="Terrain") void UpdateContacts();
private:
    UFUNCTION() void OnRep_SurfaceSize();
    FTimerHandle ScanTimer;
};
