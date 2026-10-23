// Fill out your copyright notice in the Description page of Project Settings.


#include "AbilitySystem/AbilityTask/TargetDataUnderMouse.h"
#include "AbilitySystemComponent.h"
#include "AbilitySystem/Ability/MyDamageGameplayAbility.h"
#include "test_25d/test_25d.h"

UTargetDataUnderMouse* UTargetDataUnderMouse::CreateTargetDataUnderMouse(UGameplayAbility* OwningAbility)
{
	UTargetDataUnderMouse* MyObj = NewAbilityTask<UTargetDataUnderMouse>(OwningAbility);
	return MyObj;
}

void UTargetDataUnderMouse::Activate()
{
	const bool bIsLocallyControlled = Ability->GetCurrentActorInfo()->IsLocallyControlled();
	if (bIsLocallyControlled)
	{
		SendMouseCursorData();
	}else
	{
		const FGameplayAbilitySpecHandle SpecHandle = GetAbilitySpecHandle();
		const FPredictionKey PredictionKey = GetActivationPredictionKey();

		AbilitySystemComponent.Get()->AbilityTargetDataSetDelegate(SpecHandle, PredictionKey).
			AddUObject(this, &UTargetDataUnderMouse::OnTargetDataReplicatedCallback);

		const bool bCalledDelegate= AbilitySystemComponent.Get()->CallReplicatedTargetDataDelegatesIfSet(SpecHandle, PredictionKey);
		if (!bCalledDelegate)
		{
			SetWaitingOnRemotePlayerData();
		}
	}
}

void UTargetDataUnderMouse::SendMouseCursorData()
{
	FScopedPredictionWindow ScopedPrediction(AbilitySystemComponent.Get(),true);

	APlayerController* PC = Ability->GetCurrentActorInfo()->PlayerController.Get();

	FHitResult CursorHit;
	PC->GetHitResultUnderCursor(ECC_Target, false, CursorHit);

	FGameplayAbilityTargetDataHandle DataHandle;
	FGameplayAbilityTargetData_SingleTargetHit* Data = new FGameplayAbilityTargetData_SingleTargetHit();
	Data->HitResult = CursorHit;
	DataHandle.Add(Data);
	FGameplayTag ApplicationTag;

	AbilitySystemComponent->ServerSetReplicatedTargetData(GetAbilitySpecHandle(), 
		GetActivationPredictionKey(), 
		DataHandle, 
		ApplicationTag,
		AbilitySystemComponent->ScopedPredictionKey);

	if (ShouldBroadcastAbilityTaskDelegates())
	{
		if (auto* Attack = Cast<UMyDamageGameplayAbility>(Ability)) Attack->SetOffensiveAttackTarget(CursorHit.GetActor());
		ValidData.Broadcast(DataHandle);
	}
}

void UTargetDataUnderMouse::OnTargetDataReplicatedCallback(const FGameplayAbilityTargetDataHandle& DataHandle, FGameplayTag ApplicationTag)
{
	// Keep shared target data alive after consuming the ASC's cached handle.
	const FGameplayAbilityTargetDataHandle LocalData = DataHandle;
	AbilitySystemComponent->ConsumeClientReplicatedTargetData(GetAbilitySpecHandle(), GetActivationPredictionKey());
	if (ShouldBroadcastAbilityTaskDelegates())
	{
		if (auto* Attack = Cast<UMyDamageGameplayAbility>(Ability))
		{
			const FHitResult* Hit = LocalData.Num() > 0 && LocalData.Get(0) ? LocalData.Get(0)->GetHitResult() : nullptr;
			Attack->SetOffensiveAttackTarget(Hit ? Hit->GetActor() : nullptr);
		}
		ValidData.Broadcast(LocalData);
	}
}
