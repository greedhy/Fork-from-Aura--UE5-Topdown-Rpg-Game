#pragma once
#include "CoreMinimal.h"
#include "Roguelike/DungeonGenerationController.h"
#include "Roguelike/DungeonRunTypes.h"
#include "DungeonRunController.generated.h"

class UDungeonRunWidget;
class UAbilitySystemComponent;
class UInputAction;
class UInputMappingContext;
class UEnhancedInputComponent;
class UEnhancedInputLocalPlayerSubsystem;

UCLASS()
class TEST_25D_API ADungeonRunController : public ADungeonGenerationController
{
    GENERATED_BODY()
public:
    virtual void PlayerTick(float DeltaTime) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated, BlueprintReadOnly) FDungeonPlayerRunView RunView;
    UFUNCTION(BlueprintCallable) void RequestRoomInteraction(FName RoomId, EDungeonInteraction Action, int32 OfferIndex = -1);
    UFUNCTION(Server, Reliable) void ServerRoomInteraction(FGuid RunId, FName RoomId, EDungeonInteraction Action, int32 OfferIndex);
    UFUNCTION(Client, Reliable) void ClientReturnFromDungeon();
    UFUNCTION(BlueprintCallable) void InteractNearest();
    UFUNCTION(BlueprintCallable) void ReturnToMenu();
protected:
    virtual void SetupInputComponent() override;
private:
    UPROPERTY(Transient) TObjectPtr<UDungeonRunWidget> RunWidget;
    UPROPERTY(Transient) TObjectPtr<UInputAction> InteractionAction;
    UPROPERTY(Transient) TObjectPtr<UInputMappingContext> InteractionContext;
    TWeakObjectPtr<UEnhancedInputComponent> InteractionInput;
    TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> InteractionSubsystem;
    uint32 InteractionBindingHandle = 0;
    TWeakObjectPtr<UAbilitySystemComponent> BlockedASC;
    bool bHoldingRunMovement = false;
    void UpdateActionBlock(bool bBlocked);
    void UpdateInteractionMapping();
};
