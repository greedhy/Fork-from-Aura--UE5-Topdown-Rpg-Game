// Fill out your copyright notice in the Description page of Project Settings.


#include "AbilitySystem/Ability/MyDamageGameplayAbility.h"

#include "AbilitySystemBlueprintLibrary.h"
#include"AbilitySystemComponent.h"
#include "AbilitySystem/MyAbilitySystemComponent.h"
#include "Roguelike/DungeonRunDirector.h"

void UMyDamageGameplayAbility::SetOffensiveAttackTarget(AActor* TargetActor)
{
	OffensiveAttackTarget = TargetActor;
	if (bAttackCommitted) ReportOffensiveAttack(TargetActor);
}

void UMyDamageGameplayAbility::ReportOffensiveAttack(AActor* TargetActor)
{
	OffensiveAttackTarget = TargetActor;
	if (!bAttackCommitted || !IsActive() || !CurrentActorInfo || !CurrentActorInfo->IsNetAuthority()) return;
	if (auto* ASC = Cast<UMyAbilitySystemComponent>(GetAbilitySystemComponentFromActorInfo()))
		ASC->NotifyOffensiveAttack(this, TargetActor);
}

void UMyDamageGameplayAbility::CommitExecute(const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo)
{
	Super::CommitExecute(Handle, ActorInfo, ActivationInfo);
	bAttackCommitted = true;
	ReportOffensiveAttack(OffensiveAttackTarget.Get());
}

void UMyDamageGameplayAbility::EndAbility(const FGameplayAbilitySpecHandle Handle,
	const FGameplayAbilityActorInfo* ActorInfo, const FGameplayAbilityActivationInfo ActivationInfo,
	bool bReplicateEndAbility, bool bWasCancelled)
{
	bAttackCommitted = false;
	OffensiveAttackTarget.Reset();
	Super::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
}

void UMyDamageGameplayAbility::CauseDamage(AActor* TargetActor)
{
	if (!CurrentActorInfo || !IsValid(TargetActor) || !DamageEffectClass) return;
	auto* SourceASC = GetAbilitySystemComponentFromActorInfo();
	auto* TargetASC = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(TargetActor);
	if (!IsValid(SourceASC) || !IsValid(TargetASC)) return;
	const AActor* SourceAvatar = SourceASC->GetAvatarActor();
	const AActor* TargetAvatar = TargetASC->GetAvatarActor();
	if (!IsValid(SourceAvatar) || !IsValid(TargetAvatar)
		|| !ADungeonRunDirector::AllowsCombat(SourceAvatar, TargetAvatar)) return;
	FGameplayEffectSpecHandle DamageSpecHandle = MakeOutgoingGameplayEffectSpec(DamageEffectClass, 1.f);
	if (!DamageSpecHandle.IsValid()) return;
	ReportOffensiveAttack(TargetActor);
	const float ScaleDamage = Damage.GetValueAtLevel(GetAbilityLevel());
	UAbilitySystemBlueprintLibrary::AssignTagSetByCallerMagnitude(DamageSpecHandle, DamageType, ScaleDamage);
	SourceASC->ApplyGameplayEffectSpecToTarget(*DamageSpecHandle.Data.Get(), TargetASC);
}
FTaggedMontage UMyDamageGameplayAbility::GetRandomTaggedMontageFromArray(const TArray<FTaggedMontage>& TaggedMontages)const 
{
	if (TaggedMontages.Num() > 0)
	{
		const int32 RandomNum = FMath::RandRange(0, TaggedMontages.Num() - 1);
		return TaggedMontages[RandomNum];
	}
	return FTaggedMontage();
}
float UMyDamageGameplayAbility::GetDamageAtLevel() const
{
	return Damage.GetValueAtLevel(GetAbilityLevel());
}
FDamageEffectParams UMyDamageGameplayAbility::MakeDamageEffectParamsFromClassDefaults(AActor* TargetActor,
	FVector InRadialDamageOrigin, bool bOverrideKnockbackDirection, FVector KnockbackDirectionOverride,
	bool bOverrideDeathImpulse, FVector DeathImpulseDirectionOverride, bool bOverridePitch, float PitchOverride) const
{
	FDamageEffectParams Params;
	Params.WorldContextObject = GetAvatarActorFromActorInfo();
	Params.DamageGameplayEffectClass = DamageEffectClass;
	Params.SourceAbilitySystemComponent = GetAbilitySystemComponentFromActorInfo();
	Params.TargetAbilitySystemComponent = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(TargetActor);
	Params.BaseDamage = Damage.GetValueAtLevel(GetAbilityLevel());
	Params.AbilityLevel = GetAbilityLevel();
	Params.DamageType = DamageType;
	Params.DebuffChance = DebuffChance;
	Params.DebuffDamage = DebuffDamage;
	Params.DebuffDuration = DebuffDuration;
	Params.DebuffFrequency = DebuffFrequency;
	Params.DeathImpulseMagnitude = DeathImpulseMagnitude;
	Params.KnockbackForceMagnitude = KnockbackForceMagnitude;
	Params.KnockbackChance = KnockbackChance;

	if (IsValid(TargetActor))
	{
		FRotator Rotation = (TargetActor->GetActorLocation() - GetAvatarActorFromActorInfo()->GetActorLocation()).Rotation();
		if (bOverridePitch)
		{
			Rotation.Pitch = PitchOverride;
		}
		const FVector ToTarget = Rotation.Vector();
		if (!bOverrideKnockbackDirection)
		{
			Params.KnockbackForce = ToTarget * KnockbackForceMagnitude;
		}
		if (!bOverrideDeathImpulse)
		{
			Params.DeathImpulse = ToTarget * DeathImpulseMagnitude;
		}
	}


	if (bOverrideKnockbackDirection)
	{
		KnockbackDirectionOverride.Normalize();
		Params.KnockbackForce = KnockbackDirectionOverride * KnockbackForceMagnitude;
		if (bOverridePitch)
		{
			FRotator KnockbackRotation = KnockbackDirectionOverride.Rotation();
			KnockbackRotation.Pitch = PitchOverride;
			Params.KnockbackForce = KnockbackRotation.Vector() * KnockbackForceMagnitude;
		}
	}

	if (bOverrideDeathImpulse)
	{
		DeathImpulseDirectionOverride.Normalize();
		Params.DeathImpulse = DeathImpulseDirectionOverride * DeathImpulseMagnitude;
		if (bOverridePitch)
		{
			FRotator DeathImpulseRotation = DeathImpulseDirectionOverride.Rotation();
			DeathImpulseRotation.Pitch = PitchOverride;
			Params.DeathImpulse = DeathImpulseRotation.Vector() * DeathImpulseMagnitude;
		}
	}

	if (bIsRadialDamage)
	{
		Params.bIsRadialDamage = bIsRadialDamage;
		Params.RadialDamageOrigin = InRadialDamageOrigin;
		Params.RadialDamageInnerRadius = RadialDamageInnerRadius;
		Params.RadialDamageOuterRadius = RadialDamageOuterRadius;
	}
	return Params;
}
