// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include"Input/MyInputConfig.h"
#include "UI/Widget/DamageTextComponent.h"

#include "MyPlayerController.generated.h"

class IHighLightInterface;
class UNiagaraSystem;
class USplineComponent;
class UInputMappingContext;
class UInputAction;
class UMyAbilitySystemComponent;
struct FInputActionValue;
class AMagicCircle;

/**
 * 
 */
enum class ETargetingStatus : uint8
{
	TargetingEnemy,
	TargetingNonEnemy,
	NotTargeting
};

UCLASS()
class TEST_25D_API AMyPlayerController : public APlayerController
{
	GENERATED_BODY()
	
public:
	AMyPlayerController();
	virtual void PlayerTick(float DeltaTime) override;

	UFUNCTION(Client,Reliable)
	void ShowDamageNumber(float DamageAccount,ACharacter* TargetCharacter, bool bBlockHit, bool bCriticalHit);

	UFUNCTION(BlueprintCallable)
	void ShowMagicCircle(UMaterialInterface* DecalMaterial = nullptr);

	UFUNCTION(BlueprintCallable)
	void HideMagicCircle();


protected:
	virtual void BeginPlay() override;	
	virtual void SetupInputComponent() override;

private:
	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputMappingContext> PlayerContext;

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> ShiftAction;

	void Move(const FInputActionValue& InputActionValue);
	void CursorTrace();
	void ShiftPressed() { bShiftKeyDown = true; };
	void ShiftReleased() { bShiftKeyDown = false; };
	bool bShiftKeyDown = false;

	TObjectPtr<AActor> LastActor;
	TObjectPtr<AActor> ThisActor;
	static void HighlightActor(AActor* InActor);
	static void UnHighlightActor(AActor* InActor);
	FHitResult CursorHit;
	void AbilityInputTagPressed(FGameplayTag InputTag);
	void AbilityInputTagReleased(FGameplayTag InputTag);
	void AbilityInputTagHeld(FGameplayTag InputTag);


	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UMyInputConfig> InputConfig;
	UPROPERTY()
	TObjectPtr<UMyAbilitySystemComponent> MyAbilitySystemComponent;

	UMyAbilitySystemComponent* GetASC();

	FVector CachedDestination= FVector::ZeroVector;
	float FollowTime=0.f;
	float ShortPressThreshold = 0.5f;
	bool bAutoRunning = false;

	ETargetingStatus TargetingStatus = ETargetingStatus::NotTargeting;

	UPROPERTY(EditDefaultsOnly)
	float AutoRunAcceptanceRadius = 50.f;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<USplineComponent> Spline;

	UPROPERTY(EditDefaultsOnly)
	TObjectPtr<UNiagaraSystem> ClickNiagaraSystem;



	void AutoRun();

	UPROPERTY(EditDefaultsOnly)
	TSubclassOf<UDamageTextComponent> DamageTextComponentClass;

	UPROPERTY(EditDefaultsOnly)
	TSubclassOf<AMagicCircle> MagicCircleClass;

	UPROPERTY()
	TObjectPtr<AMagicCircle> MagicCircle;

	void UpdateMagicCircleLocation();
};
