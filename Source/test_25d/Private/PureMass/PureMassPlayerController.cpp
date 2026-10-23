#include "PureMass/PureMassPlayerController.h"
#include "PureMass/PureMassSubsystem.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystem/MyAbilitySystemComponent.h"
#include "Input/MyInputComponent.h"
#include "InputActionValue.h"
#include "MyGameplayTags.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "GameFramework/Pawn.h"

UMyAbilitySystemComponent* APureMassPlayerController::MassASC() const
{
    return Cast<UMyAbilitySystemComponent>(UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(GetPawn()));
}

bool APureMassPlayerController::IsBlocked(FGameplayTag Tag) const
{
    auto* ASC = MassASC();
    return IsBackpackUIOpen() || (ASC && ASC->HasMatchingGameplayTag(Tag));
}

void APureMassPlayerController::SetupInputComponent()
{
    // Bypass the base controller's private Actor-only LMB handlers, retaining its UI/RPC support.
    APlayerController::SetupInputComponent();
    auto* Input = CastChecked<UMyInputComponent>(InputComponent);
    if (MassMoveAction) Input->BindAction(MassMoveAction, ETriggerEvent::Triggered, this, &ThisClass::MoveMass);
    if (MassShiftAction)
    {
        Input->BindAction(MassShiftAction, ETriggerEvent::Started, this, &ThisClass::ShiftDown);
        Input->BindAction(MassShiftAction, ETriggerEvent::Completed, this, &ThisClass::ShiftUp);
    }
    if (MassInputConfig) Input->BindAbilityActions(MassInputConfig, this, &ThisClass::Pressed, &ThisClass::Released, &ThisClass::Held);
}

void APureMassPlayerController::UpdateCursor()
{
    HoveredEntity = 0;
    if (IsBlocked(FMyGameplayTags::Get().Player_Block_CursorTrace)) return;
    FVector Origin, Direction;
    if (!DeprojectMousePositionToWorld(Origin, Direction)) return;
    FVector End = Origin + Direction * 100000.f;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(PureMassCursor), false, GetPawn());
    FHitResult WorldHit;
    if (GetWorld()->LineTraceSingleByChannel(WorldHit, Origin, End, ECC_Visibility, Params)) End = WorldHit.ImpactPoint;
    float Time = 1.f;
    HoveredEntity = FMath::Max(0, GetWorld()->GetSubsystem<UPureMassSubsystem>()->Sweep(Origin, End, 0.f, Time));
    if (WorldHit.bBlockingHit) MoveDestination = WorldHit.ImpactPoint;
}

void APureMassPlayerController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
    if (!IsLocalController()) return;
    UpdateCursor();
    if (IsBlocked(FMyGameplayTags::Get().Player_Block_InputHeld)) { MovePath.Reset(); return; }
    APawn* ControlledPawn = GetPawn();
    if (!ControlledPawn || !MovePath.IsValidIndex(PathIndex)) return;
    if (FVector::DistSquared2D(ControlledPawn->GetActorLocation(), MovePath[PathIndex]) < FMath::Square(55.f)) ++PathIndex;
    if (MovePath.IsValidIndex(PathIndex)) ControlledPawn->AddMovementInput((MovePath[PathIndex] - ControlledPawn->GetActorLocation()).GetSafeNormal2D());
}

void APureMassPlayerController::MoveMass(const FInputActionValue& Value)
{
    if (IsBlocked(FMyGameplayTags::Get().Player_Block_InputPressed)) return;
    MovePath.Reset();
    if (APawn* ControlledPawn = GetPawn())
    {
        const FVector2D Axis = Value.Get<FVector2D>();
        const FRotationMatrix Rotation(FRotator(0, GetControlRotation().Yaw, 0));
        ControlledPawn->AddMovementInput(Rotation.GetUnitAxis(EAxis::X), Axis.Y);
        ControlledPawn->AddMovementInput(Rotation.GetUnitAxis(EAxis::Y), Axis.X);
    }
}

void APureMassPlayerController::Pressed(FGameplayTag Tag)
{
    if (Tag.MatchesTagExact(FMyGameplayTags::Get().InputTag_Backpack)) { ToggleBackpackUI(); return; }
    if (IsBlocked(FMyGameplayTags::Get().Player_Block_InputPressed)) return;
    if (Tag.MatchesTagExact(FMyGameplayTags::Get().InputTag_Pickup)) { ServerRequestPickup(); return; }
    UpdateCursor();
    if (Tag.MatchesTagExact(FMyGameplayTags::Get().InputTag_LMB))
    {
        bLMBCombat = HoveredEntity != 0 || bMassShift;
        if (!bLMBCombat) return;
    }
    MovePath.Reset();
    if (auto* ASC = MassASC()) ASC->AbilityInputTagPressed(Tag);
}

void APureMassPlayerController::Held(FGameplayTag Tag)
{
    if (IsBlocked(FMyGameplayTags::Get().Player_Block_InputHeld)) return;
    if (Tag.MatchesTagExact(FMyGameplayTags::Get().InputTag_LMB) && !bLMBCombat)
    {
        if (APawn* ControlledPawn = GetPawn())
        {
            if (auto* Path = UNavigationSystemV1::FindPathToLocationSynchronously(this, ControlledPawn->GetActorLocation(), MoveDestination, ControlledPawn))
            { MovePath = Path->PathPoints; PathIndex = MovePath.Num() > 1 ? 1 : 0; }
        }
        return;
    }
    if (auto* ASC = MassASC()) ASC->AbilityInputTagHeld(Tag);
}

void APureMassPlayerController::Released(FGameplayTag Tag)
{
    // Release must still reach GAS when UI opens or a block tag appears during a channel.
    if (auto* ASC = MassASC()) ASC->AbilityInputTagReleased(Tag);
    if (Tag.MatchesTagExact(FMyGameplayTags::Get().InputTag_LMB)) bLMBCombat = false;
}

