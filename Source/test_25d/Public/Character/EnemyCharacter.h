// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "test_25d/test_25d.h"
#include "Character/BaseCharacter.h"
#include "Components/WidgetComponent.h"
#include "Interface/HighLightInterface.h"
#include "Interface/IEnemyInterface.h"
#include "UI/WidgetController/OverlayWidgetController.h"

#include "EnemyCharacter.generated.h"

class UBehaviorTree;
class AMyAIController;
/**
 * 
 */
UCLASS()
class TEST_25D_API AEnemyCharacter : public ABaseCharacter, public IEnemyInterface,public  IHighLightInterface
{
	GENERATED_BODY()
public:
	AEnemyCharacter();


	/** Highlight Interface */
	virtual void HighLightActor_Implementation() override;
	virtual void UnHighLightActor_Implementation() override;
	virtual void SetMoveToLocation_Implementation(FVector& OutDestination) override;
	//
	virtual void InitAbilityActorInfo() override;
	virtual void BeginPlay() override;
	virtual void Die(const FVector& DeathImpulse) override;
	virtual void PossessedBy(AController* NewController) override;

	UPROPERTY(EditAnywhere,BlueprintReadOnly ,Category = "Character Class Defaults")
	int32 Level = 1;	
	UPROPERTY(BlueprintReadOnly,Category="Combat")
	bool bHitReacting = false;

	virtual void StunTagChanged(const FGameplayTag CallbackTag, int32 NewCount);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Combat")
	float LifeSpan = 5.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Widget")
	TObjectPtr<UWidgetComponent> HealthBar;

	UPROPERTY(BlueprintAssignable)
	FOnAttributeChangedSignature OnHealthChanged;

	UPROPERTY(BlueprintAssignable)
	FOnAttributeChangedSignature OnMaxHealthChanged;

	//combat interface
	virtual int32 GetPlayerLevel_Implementation() ;

	virtual void InitlizeDefaultAttributes() const override;

	void HitReactTagChanged(const FGameplayTag CallbackTag,  int32 NewCount);

	UPROPERTY(BlueprintReadWrite, Category = "Combat")
	TObjectPtr<AActor>CombatTarget;

	/* IEnemyInterface敌人接口 */
	virtual AActor* GetCombatTarget_Implementation() const override;
	virtual void SetCombatTarget_Implementation(AActor* InCombatTarget) override;
	/* IEnemyInterface敌人接口 结束 */

	//ai 

	UPROPERTY(EditAnywhere, Category = "AI")
	TObjectPtr<UBehaviorTree> BehaviorTree;

	UPROPERTY()
	TObjectPtr<AMyAIController> MyAIController;

	void SetLevel(int32 InLevel) { Level = InLevel; }


	UFUNCTION(BlueprintImplementableEvent)
	void SpawnLoot();
private:
	
};
