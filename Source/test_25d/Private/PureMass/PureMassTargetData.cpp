#include "PureMass/PureMassTargetData.h"
#include "PureMass/PureMassSubsystem.h"
#include "PureMass/PureMassRuntime.h"
#include "PureMass/PureMassCombatTarget.h"
#include "Components/PrimitiveComponent.h"
#include "AbilitySystemComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"

UPureMassTargetData* UPureMassTargetData::Create(UGameplayAbility* Owner)
{
    return NewAbilityTask<UPureMassTargetData>(Owner);
}

void UPureMassTargetData::Activate()
{
    if (!Ability || !AbilitySystemComponent.IsValid()) { EndTask(); return; }
    const auto* Info = Ability->GetCurrentActorInfo();
    if (!Info->IsLocallyControlled())
    {
        DataDelegate = AbilitySystemComponent->AbilityTargetDataSetDelegate(GetAbilitySpecHandle(), GetActivationPredictionKey())
            .AddUObject(this, &ThisClass::Receive);
        if (!AbilitySystemComponent->CallReplicatedTargetDataDelegatesIfSet(GetAbilitySpecHandle(), GetActivationPredictionKey()))
            SetWaitingOnRemotePlayerData();
        return;
    }
    FScopedPredictionWindow Prediction(AbilitySystemComponent.Get(), true);
    FGameplayAbilityTargetDataHandle Data;
    auto* Hit = new FGameplayAbilityTargetData_SingleTargetHit();
    Data.Add(Hit);
    FVector Start, Direction;
    auto* PC = Info->PlayerController.Get();
    if (PC && PC->DeprojectMousePositionToWorld(Start, Direction))
    {
        const FVector End = Start + Direction * 100000.f;
        float EntityTime = 1.f;
        FHitResult Wall;
        const auto Target = PureMassCombat::Sweep(GetWorld(), Info->AvatarActor.Get(), Start, End, 0.f, EntityTime, Wall);
        FVector Location;
        if (Target.IsSet() && PureMassCombat::Resolve(GetWorld(), Info->AvatarActor.Get(), Target, Location))
        {
            if (AActor* Actor = Target.Actor.Get())
                Hit->HitResult = FHitResult(Actor, Cast<UPrimitiveComponent>(Actor->GetRootComponent()), Location, FVector::UpVector);
            Hit->HitResult.bBlockingHit = true;
            Hit->HitResult.Item = Target.EntityId;
            Hit->HitResult.ImpactPoint = Location;
            Hit->HitResult.Location = Hit->HitResult.ImpactPoint;
        }
        else if (Wall.bBlockingHit)
        {
            Hit->HitResult.bBlockingHit = true;
            Hit->HitResult.Item = INDEX_NONE;
            Hit->HitResult.ImpactPoint = Wall.ImpactPoint;
            Hit->HitResult.Location = Wall.ImpactPoint;
        }
    }
    if (!Info->IsNetAuthority())
        AbilitySystemComponent->ServerSetReplicatedTargetData(GetAbilitySpecHandle(), GetActivationPredictionKey(), Data,
            FGameplayTag(), AbilitySystemComponent->ScopedPredictionKey);
    if (ShouldBroadcastAbilityTaskDelegates()) Ready.Broadcast(Data);
    EndTask();
}

void UPureMassTargetData::Receive(const FGameplayAbilityTargetDataHandle& Data, FGameplayTag)
{
    const FGameplayAbilityTargetDataHandle Copy = Data;
    AbilitySystemComponent->ConsumeClientReplicatedTargetData(GetAbilitySpecHandle(), GetActivationPredictionKey());
    if (ShouldBroadcastAbilityTaskDelegates()) Ready.Broadcast(Copy);
    EndTask();
}

void UPureMassTargetData::OnDestroy(bool bAbilityEnded)
{
    if (AbilitySystemComponent.IsValid())
        AbilitySystemComponent->AbilityTargetDataSetDelegate(GetAbilitySpecHandle(), GetActivationPredictionKey()).Remove(DataDelegate);
    Super::OnDestroy(bAbilityEnded);
}
