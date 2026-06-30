// Fill out your copyright notice in the Description page of Project Settings.


#include "Character/EnemyCharacter.h"
#include "AbilitySystem/MyAbilitySystemComponent.h"
#include "AbilitySystem/MyAttributeSet.h"
#include"AbilitySystem/MyAbilitySystemLibrary.h"
#include"UI/Widget/MyUserWidget.h"
#include"MyGameplayTags.h"
#include"AI/MyAIController.h"
#include "BehaviorTree/BehaviorTree.h"
#include"BehaviorTree/BlackboardComponent.h"
#include"GameFramework/CharacterMovementComponent.h"
#include "AbilitySystem/Debuff/DebuffNiagaraComponent.h"

AEnemyCharacter::AEnemyCharacter()
{
	GetMesh()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
	HealthBar = CreateDefaultSubobject<UWidgetComponent>("HealthBar");
	HealthBar->SetupAttachment(GetRootComponent()); //将血条附件到根节点上

	AbilitySystemComponent = CreateDefaultSubobject<UMyAbilitySystemComponent>("AbilitySystemComponent");	
	AbilitySystemComponent->SetIsReplicated(true);
	AbilitySystemComponent->SetReplicationMode(EGameplayEffectReplicationMode::Minimal);
	AttributeSet = CreateDefaultSubobject<UMyAttributeSet>("AttributeSet");

	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;
	bUseControllerRotationYaw = false;
	BaseWalkSpeed = 250.f;

	GetCharacterMovement()->bUseControllerDesiredRotation = true;
	GetCharacterMovement()->MaxWalkSpeed = BaseWalkSpeed;

	Weapon->SetCustomDepthStencilValue(CUSTOM_DEPTH_RED);
	GetMesh()->SetCustomDepthStencilValue(CUSTOM_DEPTH_RED);

	Weapon->MarkRenderStateDirty();
	GetMesh()->MarkRenderStateDirty();
}

void AEnemyCharacter::HighLightActor_Implementation()
{
	GetMesh()->SetRenderCustomDepth(true);
	Weapon->SetRenderCustomDepth(true);
}

void AEnemyCharacter::UnHighLightActor_Implementation()
{
	GetMesh()->SetRenderCustomDepth(false);
	Weapon->SetRenderCustomDepth(false);
}

void AEnemyCharacter::BeginPlay()
{
	Super::BeginPlay();
	InitAbilityActorInfo();
	

	if (HasAuthority())
	{
		UMyAbilitySystemLibrary::GiveStartupAbilities(this, AbilitySystemComponent,CharacterClass);
	}

	if (UMyUserWidget* UserWidget = Cast<UMyUserWidget>(HealthBar->GetUserWidgetObject()))
	{
		UserWidget->SetWidgetController(this);
	}

	if (const UMyAttributeSet* AS = Cast<UMyAttributeSet>(AttributeSet))
	{
		//监听血量变化
		AbilitySystemComponent->GetGameplayAttributeValueChangeDelegate(AS->GetHealthAttribute()).AddLambda(
			[this](const FOnAttributeChangeData& Data)
			{
				OnHealthChanged.Broadcast(Data.NewValue);
			}
		);
		AbilitySystemComponent->GetGameplayAttributeValueChangeDelegate(AS->GetMaxHealthAttribute()).AddLambda(
			[this](const FOnAttributeChangeData& Data)
			{
				OnMaxHealthChanged.Broadcast(Data.NewValue);
			}
		);

		AbilitySystemComponent->RegisterGameplayTagEvent(FMyGameplayTags::Get().Effects_HitReact, EGameplayTagEventType::NewOrRemoved).AddUObject(
			this,&AEnemyCharacter::HitReactTagChanged

		);

		//初始化血量
		OnHealthChanged.Broadcast(AS->GetHealth());
		OnMaxHealthChanged.Broadcast(AS->GetMaxHealth());
	}

}

void AEnemyCharacter::Die(const FVector& DeathImpulse)
{
	SetLifeSpan(LifeSpan);
	if (MyAIController)
	MyAIController->GetBlackboardComponent()->SetValueAsBool(FName("Dead"), true);
	SpawnLoot();
	Super::Die(DeathImpulse);

}

void AEnemyCharacter::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);

	if (!HasAuthority())
		return;
	MyAIController=Cast<AMyAIController>(NewController);
	MyAIController->GetBlackboardComponent()->InitializeBlackboard(*BehaviorTree->BlackboardAsset);
	MyAIController->RunBehaviorTree(BehaviorTree);
	MyAIController->GetBlackboardComponent()->SetValueAsBool(FName("HitReacting"), false);
	MyAIController->GetBlackboardComponent()->SetValueAsBool(FName("RangeAttacker"), CharacterClass != ECharacterClass::Warrior);

	
}

void AEnemyCharacter::StunTagChanged(const FGameplayTag CallbackTag, int32 NewCount)
{
	Super::StunTagChanged(CallbackTag, NewCount);
	if (MyAIController && MyAIController->GetBlackboardComponent())
		MyAIController->GetBlackboardComponent()->SetValueAsBool(FName("Stun"), bIsStunned);

}

int32 AEnemyCharacter::GetPlayerLevel_Implementation()
{
	return Level;
}

void AEnemyCharacter::InitlizeDefaultAttributes() const
{
	UMyAbilitySystemLibrary::InitializeDefaultAttributes(this, CharacterClass, Level, AbilitySystemComponent);

}

void AEnemyCharacter::HitReactTagChanged(const FGameplayTag CallbackTag, int32 NewCount)
{
	 bHitReacting = NewCount > 0;
	 GetCharacterMovement()->MaxWalkSpeed = bHitReacting ? 0 : BaseWalkSpeed;
	if (MyAIController&& MyAIController->GetBlackboardComponent())
	 MyAIController->GetBlackboardComponent()->SetValueAsBool(FName("HitReacting"), bHitReacting);

}

void AEnemyCharacter::InitAbilityActorInfo()
{
	AbilitySystemComponent->InitAbilityActorInfo(this, this);
	UMyAbilitySystemComponent* UmyASC = Cast<UMyAbilitySystemComponent>(AbilitySystemComponent);
		UmyASC->AbilityActorInfoSet();
		
		if (HasAuthority()) {
			InitlizeDefaultAttributes();
		}
		OnASCRegistered.Broadcast(AbilitySystemComponent);

		AbilitySystemComponent->RegisterGameplayTagEvent(FMyGameplayTags::Get().Debuff_Stun, EGameplayTagEventType::NewOrRemoved).
			AddUObject(this, &ABaseCharacter::StunTagChanged);

}
AActor* AEnemyCharacter::GetCombatTarget_Implementation() const
{
	return CombatTarget;
}

void AEnemyCharacter::SetCombatTarget_Implementation(AActor* InCombatTarget)
{
	CombatTarget = InCombatTarget;
}

void AEnemyCharacter::SetMoveToLocation_Implementation(FVector& OutDestination)
{
	// Do not change OutDestination
}