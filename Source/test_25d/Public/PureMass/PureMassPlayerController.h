#pragma once

#include "CoreMinimal.h"
#include "Player/MyPlayerController.h"
#include "PureMassPlayerController.generated.h"

struct FInputActionValue;

/** Cosmetic damage payload, independent of entity lifetime and replication snapshots. */
USTRUCT()
struct FPureMassDamageNumber
{
    GENERATED_BODY()
    UPROPERTY() int32 EntityId = INDEX_NONE;
    UPROPERTY() FVector_NetQuantize Position = FVector::ZeroVector;
    UPROPERTY() float Damage = 0.f;
    UPROPERTY() bool bBlocked = false;
    UPROPERTY() bool bCritical = false;
};

/** New controller for copied Mass maps; no Actor proxy is needed for cursor targeting. */
UCLASS()
class TEST_25D_API APureMassPlayerController : public AMyPlayerController
{
    GENERATED_BODY()
public:
    APureMassPlayerController();
    virtual void PlayerTick(float DeltaTime) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    void QueueMassDamageNumber(int32 EntityId, FVector Position, float Damage, bool bBlocked, bool bCritical);
    UPROPERTY(EditDefaultsOnly, Category="Pure Mass|Feedback") TSubclassOf<UDamageTextComponent> MassDamageTextComponentClass;
    UPROPERTY(EditDefaultsOnly, Category="Pure Mass|Input") TObjectPtr<UMyInputConfig> MassInputConfig;
    UPROPERTY(EditDefaultsOnly, Category="Pure Mass|Input") TObjectPtr<UInputAction> MassMoveAction;
    UPROPERTY(EditDefaultsOnly, Category="Pure Mass|Input") TObjectPtr<UInputAction> MassShiftAction;
    UFUNCTION(BlueprintPure, Category="Pure Mass") int32 GetHoveredEntity() const { return HoveredEntity; }
    UFUNCTION(BlueprintPure, Category="Pure Mass") AActor* GetHoveredCombatActor() const { return HoveredActor.Get(); }
protected:
    virtual void SetupInputComponent() override;
private:
    void FlushMassDamageNumbers();
    UFUNCTION(Client, Unreliable) void ClientShowMassDamageNumbers(const TArray<FPureMassDamageNumber>& Numbers);
    TArray<FPureMassDamageNumber> PendingDamageNumbers;
    TArray<TWeakObjectPtr<UDamageTextComponent>> ActiveDamageNumbers;
    // Screen-space WidgetComponent refuses to render when its owning Actor is hidden.
    // Controllers are hidden; one local, visible anchor owns all transient numbers instead.
    UPROPERTY(Transient) TObjectPtr<AActor> DamageNumberAnchor;
    FTimerHandle DamageNumberTimer;
    UMyAbilitySystemComponent* MassASC() const;
    void MoveMass(const FInputActionValue& Value);
    void Pressed(FGameplayTag Tag);
    void Released(FGameplayTag Tag);
    void Held(FGameplayTag Tag);
    void ShiftDown() { bMassShift = true; }
    void ShiftUp() { bMassShift = false; }
    void UpdateCursor();
    bool IsBlocked(FGameplayTag Tag) const;
    bool bMassShift = false;
    bool bLMBCombat = false;
    int32 HoveredEntity = 0;
    TWeakObjectPtr<AActor> HoveredActor;
    FVector MoveDestination = FVector::ZeroVector;
    TArray<FVector> MovePath;
    int32 PathIndex = 0;
};
