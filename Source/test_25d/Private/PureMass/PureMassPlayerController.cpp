#include "PureMass/PureMassPlayerController.h"
#include "PureMass/PureMassCombatTarget.h"
#include "PureMass/PureMassSubsystem.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystem/MyAbilitySystemComponent.h"
#include "Input/MyInputComponent.h"
#include "InputActionValue.h"
#include "MyGameplayTags.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "GameFramework/Pawn.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

APureMassPlayerController::APureMassPlayerController()
{
    static ConstructorHelpers::FClassFinder<UDamageTextComponent> Feedback(
        TEXT("/Game/BluePrints/UI/FloatingText/BP_DamageTextComponent"));
    MassDamageTextComponentClass = Feedback.Class;
}

void APureMassPlayerController::QueueMassDamageNumber(int32 EntityId, FVector Position, float Damage, bool bBlocked, bool bCritical)
{
    if (!HasAuthority() || EntityId <= 0 || Position.ContainsNaN() || !FMath::IsFinite(Damage) || Damage <= 0.f) return;
    auto* Number = PendingDamageNumbers.FindByPredicate([=](const FPureMassDamageNumber& Item)
        { return Item.EntityId == EntityId && Item.bBlocked == bBlocked && Item.bCritical == bCritical; });
    if (!Number)
    {
        if (PendingDamageNumbers.Num() >= 256) return;
        Number = &PendingDamageNumbers.AddDefaulted_GetRef();
        Number->EntityId = EntityId; Number->bBlocked = bBlocked; Number->bCritical = bCritical;
    }
    Number->Damage = FMath::Min(MAX_flt - Damage, Number->Damage) + Damage;
    Number->Position = Position;
    // DOT and terrain operate every Mass update. Batch before sending or creating any UI.
    if (!GetWorldTimerManager().IsTimerActive(DamageNumberTimer))
        GetWorldTimerManager().SetTimer(DamageNumberTimer, this, &ThisClass::FlushMassDamageNumbers, .1f, false);
}

void APureMassPlayerController::FlushMassDamageNumbers()
{
    if (!PendingDamageNumbers.IsEmpty()) ClientShowMassDamageNumbers(PendingDamageNumbers);
    PendingDamageNumbers.Reset();
}

void APureMassPlayerController::ClientShowMassDamageNumbers_Implementation(const TArray<FPureMassDamageNumber>& Numbers)
{
    if (!IsLocalController() || !MassDamageTextComponentClass || GetNetMode() == NM_DedicatedServer) return;
    if (!IsValid(DamageNumberAnchor))
    {
        FActorSpawnParameters Spawn;
        Spawn.Owner = this;
        Spawn.ObjectFlags |= RF_Transient;
        DamageNumberAnchor = GetWorld()->SpawnActor<AActor>(Spawn);
        if (!DamageNumberAnchor) return;
        DamageNumberAnchor->SetActorHiddenInGame(false);
        DamageNumberAnchor->SetActorEnableCollision(false);
    }
    ActiveDamageNumbers.RemoveAll([](const auto& Weak) { return !Weak.IsValid() || !Weak->IsRegistered(); });
    for (int32 Index = 0; Index < FMath::Min(Numbers.Num(), 256); ++Index)
    {
        const auto& Number = Numbers[Index];
        if (!FMath::IsFinite(Number.Damage) || Number.Damage <= 0.f || Number.Position.ContainsNaN()) continue;
        if (ActiveDamageNumbers.Num() >= 256)
        {
            if (auto* Oldest = ActiveDamageNumbers[0].Get()) Oldest->DestroyComponent();
            ActiveDamageNumbers.RemoveAt(0);
        }
        auto* Text = NewObject<UDamageTextComponent>(DamageNumberAnchor, MassDamageTextComponentClass);
        const FVector StyleOffset = Text->GetRelativeLocation();
        Text->SetOwnerPlayer(GetLocalPlayer());
        Text->RegisterComponent();
        Text->SetWorldLocation(FVector(Number.Position) + StyleOffset);
        Text->SetDamageText(Number.Damage, Number.bBlocked, Number.bCritical);
        ActiveDamageNumbers.Add(Text);
    }
}

void APureMassPlayerController::EndPlay(EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(DamageNumberTimer);
    PendingDamageNumbers.Reset();
    for (const auto& Weak : ActiveDamageNumbers) if (auto* Text = Weak.Get()) Text->DestroyComponent();
    ActiveDamageNumbers.Reset();
    if (IsValid(DamageNumberAnchor)) DamageNumberAnchor->Destroy();
    DamageNumberAnchor = nullptr;
    Super::EndPlay(Reason);
}

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
    HoveredActor.Reset();
    if (IsBlocked(FMyGameplayTags::Get().Player_Block_CursorTrace)) return;
    FVector Origin, Direction;
    if (!DeprojectMousePositionToWorld(Origin, Direction)) return;
    FVector End = Origin + Direction * 100000.f;
    FHitResult WorldHit;
    float Time = 1.f;
    const auto Target = PureMassCombat::Sweep(GetWorld(), GetPawn(), Origin, End, 0.f, Time, WorldHit);
    HoveredEntity = FMath::Max(0, Target.EntityId);
    HoveredActor = Target.Actor;
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
        bLMBCombat = HoveredEntity != 0 || HoveredActor.IsValid() || bMassShift;
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

