#include "Roguelike/DungeonRunController.h"
#include "Roguelike/DungeonRunDirector.h"
#include "Roguelike/DungeonRunWidget.h"
#include "Roguelike/DungeonPlayerCharacter.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystemComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "Engine/GameInstance.h"
#include "Engine/LocalPlayer.h"
#include "Online/RoomSubsystem.h"
#include "MyGameplayTags.h"
#include "InputCoreTypes.h"
#include "Net/UnrealNetwork.h"

namespace
{
FGameplayTagContainer DungeonRunInputTags()
{
    const auto& Tags = FMyGameplayTags::Get();
    FGameplayTagContainer Result;
    Result.AddTag(Tags.Player_Block_InputPressed);
    Result.AddTag(Tags.Player_Block_InputHeld);
    Result.AddTag(Tags.Player_Block_InputReleased);
    Result.AddTag(Tags.Player_Block_CursorTrace);
    return Result;
}
void LeaveLocalDungeon(ADungeonRunController* Controller)
{
    if (!Controller || !Controller->IsLocalController()) return;
    if (auto* LocalPlayer = Controller->GetLocalPlayer())
        if (auto* Instance = LocalPlayer->GetGameInstance())
            if (auto* Rooms = Instance->GetSubsystem<URoomSubsystem>()) Rooms->LeaveRoom();
}
}

void ADungeonRunController::PlayerTick(float DeltaTime)
{
    // The local player may attach after SetupInputComponent (notably on a joining client).
    UpdateInteractionMapping();
    const auto* Director = ADungeonRunDirector::Find(GetWorld());
    const bool bHold = !Director || !Director->CanPlayerAct(this);
    if (IsLocalController() && bHold != bHoldingRunMovement)
    {
        // GenerationController owns a separate counter contribution.
        SetIgnoreMoveInput(bHold);
        bHoldingRunMovement = bHold;
    }
    UpdateActionBlock(bHold);
    Super::PlayerTick(DeltaTime);
    if (IsLocalController() && GetLocalPlayer() && GetNetMode() != NM_DedicatedServer)
    {
        if (!IsValid(RunWidget)) RunWidget = CreateWidget<UDungeonRunWidget>(this, UDungeonRunWidget::StaticClass());
        if (RunWidget && !RunWidget->IsInViewport()) RunWidget->AddToPlayerScreen(100);
    }
}

void ADungeonRunController::EndPlay(EEndPlayReason::Type Reason)
{
    if (auto* Input = InteractionInput.Get()) Input->RemoveBindingByHandle(InteractionBindingHandle);
    InteractionInput.Reset();
    if (auto* Subsystem = InteractionSubsystem.Get(); Subsystem && InteractionContext)
        Subsystem->RemoveMappingContext(InteractionContext);
    InteractionSubsystem.Reset();
    if (RunWidget) { RunWidget->RemoveFromParent(); RunWidget = nullptr; }
    if (bHoldingRunMovement) { SetIgnoreMoveInput(false); bHoldingRunMovement = false; }
    UpdateActionBlock(false);
    Super::EndPlay(Reason);
}

void ADungeonRunController::SetupInputComponent()
{
    if (auto* Previous = InteractionInput.Get()) Previous->RemoveBindingByHandle(InteractionBindingHandle);
    InteractionInput.Reset();
    Super::SetupInputComponent();
    auto* Input = Cast<UEnhancedInputComponent>(InputComponent);
    if (!Input) return;
    if (!InteractionAction)
    {
        InteractionAction = NewObject<UInputAction>(this, TEXT("DungeonInteractionAction"));
        InteractionAction->ValueType = EInputActionValueType::Boolean;
        InteractionAction->bConsumeInput = false;
    }
    if (!InteractionContext)
    {
        InteractionContext = NewObject<UInputMappingContext>(this, TEXT("DungeonInteractionContext"));
        InteractionContext->MapKey(InteractionAction, EKeys::F);
    }
    InteractionBindingHandle = Input->BindAction(InteractionAction, ETriggerEvent::Started,
        this, &ThisClass::InteractNearest).GetHandle();
    InteractionInput = Input;
    UpdateInteractionMapping();
}

void ADungeonRunController::UpdateInteractionMapping()
{
    if (!InteractionContext) return;
    auto* Desired = IsLocalController() && GetLocalPlayer()
        ? ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()) : nullptr;
    if (InteractionSubsystem.Get() != Desired)
    {
        if (auto* Previous = InteractionSubsystem.Get()) Previous->RemoveMappingContext(InteractionContext);
        InteractionSubsystem = Desired;
    }
    // The inherited player mapping uses priority zero; this context owns only the F interaction.
    if (Desired && !Desired->HasMappingContext(InteractionContext)) Desired->AddMappingContext(InteractionContext, 1);
}
void ADungeonRunController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ADungeonRunController, RunView);
}
void ADungeonRunController::RequestRoomInteraction(FName RoomId, EDungeonInteraction Action, int32 OfferIndex)
{
    if (IsLocalController() || HasAuthority()) ServerRoomInteraction(RunView.RunId, RoomId, Action, OfferIndex);
}

void ADungeonRunController::ServerRoomInteraction_Implementation(FGuid RequestRunId, FName RoomId, EDungeonInteraction Action, int32 OfferIndex)
{
    if (auto* Director = ADungeonRunDirector::Find(GetWorld()))
        Director->HandleInteraction(this, RequestRunId, RoomId, Action, OfferIndex);
}

void ADungeonRunController::ClientReturnFromDungeon_Implementation() { LeaveLocalDungeon(this); }

void ADungeonRunController::InteractNearest()
{
    const auto* Director = ADungeonRunDirector::Find(GetWorld());
    if (!Director || !RunView.bCanInteract || !Director->CanPlayerAct(this)) return;
    const auto* Room = Director->Rooms.FindByPredicate([this](const FDungeonRoomProgress& Entry) { return Entry.RoomId == RunView.CurrentRoom; });
    if (!Room) return;
    switch (Room->Role)
    {
    case EDungeonRoomRole::Treasure: RequestRoomInteraction(Room->RoomId, EDungeonInteraction::ClaimTreasure); break;
    case EDungeonRoomRole::Rest: RequestRoomInteraction(Room->RoomId, EDungeonInteraction::Rest); break;
    case EDungeonRoomRole::Boss:
        if (Director->Phase == EDungeonRunPhase::Victory) RequestRoomInteraction(Room->RoomId, EDungeonInteraction::Exit);
        break;
    default: break; // Nearby merchant stock is shown as three explicit purchase buttons.
    }
}

void ADungeonRunController::ReturnToMenu()
{
    const auto* Director = ADungeonRunDirector::Find(GetWorld());
    if (Director && (Director->Phase == EDungeonRunPhase::Victory || Director->Phase == EDungeonRunPhase::Finished ||
        Director->Phase == EDungeonRunPhase::Failed)) LeaveLocalDungeon(this);
}

void ADungeonRunController::UpdateActionBlock(bool bBlocked)
{
    auto* Desired = bBlocked ? UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(GetPawn()) : nullptr;
    if (BlockedASC.Get() == Desired) return;
    if (auto* Previous = BlockedASC.Get()) Previous->RemoveLooseGameplayTags(DungeonRunInputTags());
    BlockedASC = Desired;
    if (Desired) Desired->AddLooseGameplayTags(DungeonRunInputTags());
}
