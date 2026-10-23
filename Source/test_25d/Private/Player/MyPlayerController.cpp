// Fill out your copyright notice in the Description page of Project Settings.


#include "Player/MyPlayerController.h"
#include <EnhancedInputSubsystems.h>

#include "AbilitySystemBlueprintLibrary.h"
#include "EnhancedInputComponent.h"
#include "MyGameplayTags.h"
#include "NavigationSystem.h"
#include"NavigationPath.h"
#include "NiagaraFunctionLibrary.h"
#include "AbilitySystem/MyAbilitySystemComponent.h"
#include "Components/SplineComponent.h"
#include "Input/MyInputComponent.h"
#include"GameFramework/Character.h"
#include "Actor/MagicCircle.h"
#include"Components/DecalComponent.h"
#include "Interface/HighLightInterface.h"
#include "Interface/IEnemyInterface.h"
#include "Backpack/BackpackComponent.h"
#include "Backpack/WorldPickupComponent.h"
#include "Player/MyPlayerState.h"
#include "UI/Widget/MyUserWidget.h"
#include "UI/Widget/BackpackWidget.h"
#include "UI/ViewModel/MVVM_Backpack.h"
#include "test_25d/test_25d.h"
#include "TimerManager.h"

AMyPlayerController::AMyPlayerController()
{
	bReplicates = true;
	LastActor = nullptr;
	ThisActor = nullptr;
	Spline=CreateDefaultSubobject<USplineComponent>("Spline");

}

void AMyPlayerController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
	CursorTrace();

	AutoRun();
	UpdateMagicCircleLocation();
}
void AMyPlayerController::ShowDamageNumber_Implementation(float DamageAccount, ACharacter* TargetCharacter, bool bBlockHit, bool bCriticalHit)
{
	if (IsValid(TargetCharacter)&& DamageTextComponentClass&&IsLocalController())
	{
		UDamageTextComponent* DamageText = NewObject<UDamageTextComponent>(TargetCharacter, DamageTextComponentClass);
		DamageText->RegisterComponent();
		DamageText->AttachToComponent(TargetCharacter->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);


		DamageText->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
		DamageText->SetDamageText(DamageAccount, bBlockHit, bCriticalHit);
		
	}
}

void AMyPlayerController::ServerRequestPickup_Implementation()
{
	if (!HasAuthority())
	{
		return;
	}

	AActor* PickupActor = GetRandomOverlappingInteractPickup();
	if (UWorldPickupComponent* PickupComponent = IsValid(PickupActor) ? PickupActor->FindComponentByClass<UWorldPickupComponent>() : nullptr)
	{
		if (PickupComponent->GetPickupMode() != EPickupMode::Interact)
		{
			return;
		}
		APawn* ControlledPawn = GetPawn();
		if (IsValid(ControlledPawn))
		{
			PickupComponent->TryPickup(GetPlayerState<AMyPlayerState>());
		}
		return;
	}

}

void AMyPlayerController::ServerRequestDropWholeStack_Implementation(int32 SlotIndex)
{
	if (!HasAuthority())
	{
		return;
	}

	APawn* ControlledPawn = GetPawn();
	AMyPlayerState* MyPlayerState = GetPlayerState<AMyPlayerState>();
	if (!IsValid(ControlledPawn) || !IsValid(MyPlayerState))
	{
		return;
	}

	const FVector DropLocation = ControlledPawn->GetActorLocation() + ControlledPawn->GetActorForwardVector() * 100.f;
	MyPlayerState->GetBackpackComponent()->DropWholeStack(SlotIndex, DropLocation);
}

void AMyPlayerController::ToggleBackpackUI()
{
	if (bBackpackUIOpen) CloseBackpackUI();
	else OpenBackpackUI();
}

void AMyPlayerController::OpenBackpackUI()
{
	if (!IsLocalController() || !BackpackWidgetClass) return;
	// TileView creates and binds its entry widgets on the first layout pass.  Keep that
	// initialization frame invisible so the entry template cannot flash on screen.
	if (!IsValid(BackpackWidget))
	{
		BackpackWidget = CreateWidget<UUserWidget>(this, BackpackWidgetClass);
		if (AMyPlayerState* MyPlayerState = GetPlayerState<AMyPlayerState>())
		{
			MyPlayerState->GetBackpackComponent()->InventoryVM->OnDropRequested.AddWeakLambda(this, [this](int32 SlotIndex)
			{
				ServerRequestDropWholeStack(SlotIndex);
			});
			if (UBackpackWidget* BackpackUI = Cast<UBackpackWidget>(BackpackWidget))
			{
				BackpackUI->SetBackpackViewModel(MyPlayerState->GetBackpackComponent()->InventoryVM);
			}
			else if (UMyUserWidget* WidgetWithController = Cast<UMyUserWidget>(BackpackWidget))
			{
				WidgetWithController->SetWidgetController(MyPlayerState->GetBackpackComponent()->InventoryVM);
			}
		}
	}
	BackpackWidget->SetRenderOpacity(0.f);
	BackpackWidget->AddToViewport();
	bBackpackUIOpen = true;
	BackpackWidget->ForceLayoutPrepass();
	GetWorldTimerManager().SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		if (bBackpackUIOpen && IsValid(BackpackWidget))
		{
			BackpackWidget->SetRenderOpacity(1.f);
		}
	}));
	bShowMouseCursor = true;
	FInputModeGameAndUI InputMode;
	InputMode.SetWidgetToFocus(BackpackWidget->TakeWidget());
	InputMode.SetHideCursorDuringCapture(false);
	SetInputMode(InputMode);
}

void AMyPlayerController::CloseBackpackUI()
{
	if (!IsLocalController() || !IsValid(BackpackWidget)) return;
	BackpackWidget->RemoveFromParent();
	bBackpackUIOpen = false;
	bShowMouseCursor = true;
	FInputModeGameAndUI InputMode;
	InputMode.SetHideCursorDuringCapture(false);
	SetInputMode(InputMode);
}

void AMyPlayerController::ServerRequestSwap_Implementation(int32 SourceSlotIndex, int32 TargetSlotIndex)
{
	if (!HasAuthority())
	{
		UE_LOG(LogTemp, Warning, TEXT("[BackpackDrag] Swap RPC ignored without server authority: %d -> %d."), SourceSlotIndex, TargetSlotIndex);
		return;
	}

	if (AMyPlayerState* MyPlayerState = GetPlayerState<AMyPlayerState>())
	{
		const bool bSwapped = MyPlayerState->GetBackpackComponent()->SwapSlots(SourceSlotIndex, TargetSlotIndex);
		UE_LOG(LogTemp, Log, TEXT("[BackpackDrag] Server received swap RPC %d -> %d; result=%s."), SourceSlotIndex, TargetSlotIndex, bSwapped ? TEXT("true") : TEXT("false"));
		return;
	}

	UE_LOG(LogTemp, Warning, TEXT("[BackpackDrag] Server rejected swap RPC %d -> %d: PlayerState unavailable."), SourceSlotIndex, TargetSlotIndex);
}

void AMyPlayerController::ServerRequestUse_Implementation(int32 SlotIndex)
{
	if (!HasAuthority())
	{
		return;
	}

	if (AMyPlayerState* MyPlayerState = GetPlayerState<AMyPlayerState>())
	{
		MyPlayerState->GetBackpackComponent()->TryUseItemForPawn(SlotIndex, GetPawn());
	}
}
void AMyPlayerController::AutoRun()
{
	if (!bAutoRunning)
		return;
	APawn* ControlledPawn = GetPawn();
	if (ControlledPawn)
	{
		const FVector LocationOnSpline = Spline->FindLocationClosestToWorldLocation
		(ControlledPawn->GetActorLocation(), ESplineCoordinateSpace::World);

		const FVector Direction = Spline->FindDirectionClosestToWorldLocation
		(LocationOnSpline, ESplineCoordinateSpace::World);

		ControlledPawn->AddMovementInput(Direction);
		const float DistanceToDestination = (LocationOnSpline - CachedDestination).Length();
		if (DistanceToDestination <= AutoRunAcceptanceRadius)
		{
			bAutoRunning = false;
		}
	}
}


void AMyPlayerController::BeginPlay()
{
	Super::BeginPlay();
	InitializeLocalInput();
}

void AMyPlayerController::ReceivedPlayer()
{
	Super::ReceivedPlayer();
	InitializeLocalInput();
}

void AMyPlayerController::AcknowledgePossession(APawn* P)
{
	Super::AcknowledgePossession(P);
	MyAbilitySystemComponent=nullptr;
	bAutoRunning=false; FollowTime=0.f; bShiftKeyDown=false;
	TargetingStatus=ETargetingStatus::NotTargeting;
	LastActor=nullptr; ThisActor=nullptr;
	Spline->ClearSplinePoints();
	InitializeLocalInput();
}

void AMyPlayerController::InitializeLocalInput()
{
	if (!IsLocalController() || !GetLocalPlayer()) return;
	check(PlayerContext);
	UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer());		
	if(Subsystem)
	Subsystem->AddMappingContext(PlayerContext, 0);
	bShowMouseCursor = true;
	DefaultMouseCursor = EMouseCursor::Default;
	FInputModeGameAndUI InputModeData;
	InputModeData.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	InputModeData.SetHideCursorDuringCapture(false);
	SetInputMode(InputModeData);
}

void AMyPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();	
	UMyInputComponent* MyInputComponent = CastChecked<UMyInputComponent>(InputComponent);

	MyInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AMyPlayerController::Move);
	MyInputComponent->BindAction(ShiftAction, ETriggerEvent::Started, this, &AMyPlayerController::ShiftPressed);
	MyInputComponent->BindAction(ShiftAction, ETriggerEvent::Completed, this, &AMyPlayerController::ShiftReleased);

	MyInputComponent->BindAbilityActions(InputConfig, this,
		&ThisClass::AbilityInputTagPressed, &ThisClass::AbilityInputTagReleased, &ThisClass::AbilityInputTagHeld);

}

void AMyPlayerController::Move(const FInputActionValue& InputActionValue)
{
	if (GetASC() && GetASC()->HasMatchingGameplayTag(FMyGameplayTags::Get().Player_Block_InputPressed))
	{
		return;
	}

	const FVector2D MoveVector = InputActionValue.Get<FVector2D>();
	const FRotator Rotation = GetControlRotation();
	const FRotator YawRotation(0.f, Rotation.Yaw, 0.f);

	const FVector ForwardDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);
	const FVector RightDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);

	if (APawn* ControlledPawn = GetPawn< APawn>())
	{
		ControlledPawn->AddMovementInput(ForwardDirection, MoveVector.Y);
		ControlledPawn->AddMovementInput(RightDirection, MoveVector.X);
	}
}

void AMyPlayerController::CursorTrace()
{
	if (GetASC() && GetASC()->HasMatchingGameplayTag(FMyGameplayTags::Get().Player_Block_CursorTrace))
	{
		UnHighlightActor(LastActor);
		UnHighlightActor(ThisActor);
		if (IsValid(ThisActor) && ThisActor->Implements<UHighLightInterface>())

			LastActor = nullptr;
		ThisActor = nullptr;
		return;
	}
	const ECollisionChannel TraceChannel = IsValid(MagicCircle) ? ECC_ExcludePlayers : ECC_Visibility;
	GetHitResultUnderCursor(TraceChannel, false, CursorHit);
	if (!CursorHit.bBlockingHit) return;

	LastActor = ThisActor;
	if (IsValid(CursorHit.GetActor()) && CursorHit.GetActor()->Implements<UHighLightInterface>())
	{
		ThisActor = CursorHit.GetActor();
	}
	else
	{
		ThisActor = nullptr;
	}

	if (LastActor != ThisActor)
	{
		UnHighlightActor(LastActor);
		HighlightActor(ThisActor);
	}
}

void AMyPlayerController::AbilityInputTagPressed(FGameplayTag InputTag)
{
	if (GetASC() && GetASC()->HasMatchingGameplayTag(FMyGameplayTags::Get().Player_Block_InputPressed))
	{
		return;
	}
	if (InputTag.MatchesTagExact(FMyGameplayTags::Get().InputTag_Backpack))
	{
		ToggleBackpackUI();
		return;
	}
	if (InputTag.MatchesTagExact(FMyGameplayTags::Get().InputTag_Pickup))
	{
		RequestPickupFocusedActor();
		return;
	}
	if (InputTag.MatchesTagExact(FMyGameplayTags::Get().InputTag_LMB))
	{
		if (IsValid(ThisActor))
		{
			TargetingStatus = ThisActor->Implements<UEnemyInterface>() ? ETargetingStatus::TargetingEnemy : ETargetingStatus::TargetingNonEnemy;
		}
		else
		{
			TargetingStatus = ETargetingStatus::NotTargeting;
		}
		bAutoRunning = false;
	}
	if (GetASC()) GetASC()->AbilityInputTagPressed(InputTag);
}

void AMyPlayerController::RequestPickupFocusedActor()
{
	ServerRequestPickup();
}

void AMyPlayerController::RegisterOverlappingInteractPickup(AActor* PickupActor)
{
	if (IsValid(PickupActor))
	{
		++OverlappingInteractPickups.FindOrAdd(PickupActor);
	}
}

void AMyPlayerController::UnregisterOverlappingInteractPickup(AActor* PickupActor)
{
	if (int32* OverlapCount = OverlappingInteractPickups.Find(PickupActor))
	{
		if (--(*OverlapCount) <= 0)
		{
			OverlappingInteractPickups.Remove(PickupActor);
		}
	}
}

AActor* AMyPlayerController::GetRandomOverlappingInteractPickup()
{
	TArray<AActor*> Candidates;
	for (auto It = OverlappingInteractPickups.CreateIterator(); It; ++It)
	{
		if (IsValid(It.Key().Get()) && It.Value() > 0)
		{
			Candidates.Add(It.Key().Get());
		}
		else
		{
			It.RemoveCurrent();
		}
	}

	return Candidates.IsEmpty() ? nullptr : Candidates[FMath::RandHelper(Candidates.Num())];
}

int32 AMyPlayerController::GetOverlappingInteractPickupCount() const
{
	return OverlappingInteractPickups.Num();
}

void AMyPlayerController::AbilityInputTagReleased(FGameplayTag InputTag)
{
	if (GetASC() && GetASC()->HasMatchingGameplayTag(FMyGameplayTags::Get().Player_Block_InputReleased))
	{
		return;
	}

	if (!InputTag.MatchesTagExact(FMyGameplayTags::Get().InputTag_LMB))
	{

		if (GetASC())
			GetASC()->AbilityInputTagReleased(InputTag);
		return;
	}

	if (GetASC())
		GetASC()->AbilityInputTagReleased(InputTag);
	if (TargetingStatus != ETargetingStatus::TargetingEnemy && !bShiftKeyDown)
	{
		APawn* ControlledPawn = GetPawn();
		if (FollowTime <= ShortPressThreshold && ControlledPawn)
		{
			if (IsValid(ThisActor) && ThisActor->Implements<UHighLightInterface>())
			{
				IHighLightInterface::Execute_SetMoveToLocation(ThisActor, CachedDestination);
			}
			else {

				if (GetASC() && !GetASC()->HasMatchingGameplayTag(FMyGameplayTags::Get().Player_Block_InputPressed))
				{
					UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, ClickNiagaraSystem, CachedDestination);
				}
			}
			UNavigationPath* NavPath = UNavigationSystemV1::FindPathToLocationSynchronously(this,
				ControlledPawn->GetActorLocation(), CachedDestination);
			if (NavPath)
			{
				Spline->ClearSplinePoints();
				for (const FVector& PointLoc : NavPath->PathPoints)
				{
					Spline->AddSplinePoint(PointLoc, ESplineCoordinateSpace::World);
				}
				//与示例不同，示例中多次无效目标会导致数组越界
				if (NavPath->PathPoints.Num())
					CachedDestination = NavPath->PathPoints.Last();
				else
					CachedDestination = ControlledPawn->GetActorLocation();
				bAutoRunning = true;
			}

		}
		FollowTime = 0.f;
		TargetingStatus = ETargetingStatus::NotTargeting;
	}


}

void AMyPlayerController::AbilityInputTagHeld(FGameplayTag InputTag)
{
	if (GetASC() && GetASC()->HasMatchingGameplayTag(FMyGameplayTags::Get().Player_Block_InputHeld))
	{
		return;
	}
	if (!InputTag.MatchesTagExact(FMyGameplayTags::Get().InputTag_LMB))
	{
		if (GetASC()) GetASC()->AbilityInputTagHeld(InputTag);
		return;
	}

	if (TargetingStatus == ETargetingStatus::TargetingEnemy || bShiftKeyDown)
	{
		if (GetASC()) GetASC()->AbilityInputTagHeld(InputTag);
	}
	else
	{
		FollowTime += GetWorld()->GetDeltaSeconds();
		if (CursorHit.bBlockingHit) CachedDestination = CursorHit.ImpactPoint;

		if (APawn* ControlledPawn = GetPawn())
		{
			const FVector WorldDirection = (CachedDestination - ControlledPawn->GetActorLocation()).GetSafeNormal();
			ControlledPawn->AddMovementInput(WorldDirection);
		}
	}
}

UMyAbilitySystemComponent* AMyPlayerController::GetASC()
{
	MyAbilitySystemComponent = Cast<UMyAbilitySystemComponent>(UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(GetPawn()));
	return MyAbilitySystemComponent;
}

void AMyPlayerController::UpdateMagicCircleLocation()
{
	if (IsValid(MagicCircle))
	{
		MagicCircle->SetActorLocation(CursorHit.ImpactPoint);
	}
}
void AMyPlayerController::ShowMagicCircle(UMaterialInterface* DecalMaterial)
{
	if (!IsValid(MagicCircle))
	{
		MagicCircle = GetWorld()->SpawnActor<AMagicCircle>(MagicCircleClass);
		if (DecalMaterial)
		{
			MagicCircle->MagicCircleDecal->SetMaterial(0, DecalMaterial);
		}
	}
}

void AMyPlayerController::HideMagicCircle()
{
	if (IsValid(MagicCircle))
	{
		MagicCircle->Destroy();
	}
}

void AMyPlayerController::HighlightActor(AActor* InActor)
{
	if (IsValid(InActor) && InActor->Implements<UHighLightInterface>())
	{
		IHighLightInterface::Execute_HighLightActor(InActor);
	}
}

void AMyPlayerController::UnHighlightActor(AActor* InActor)
{
	if (IsValid(InActor) && InActor->Implements<UHighLightInterface>())
	{
		IHighLightInterface::Execute_UnHighLightActor(InActor);
	}
}
