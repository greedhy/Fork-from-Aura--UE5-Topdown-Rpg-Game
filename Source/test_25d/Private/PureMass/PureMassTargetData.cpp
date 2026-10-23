#include "PureMass/PureMassTargetData.h"
#include "PureMass/PureMassSubsystem.h"
#include "PureMass/PureMassRuntime.h"
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
    auto* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
    if (PC && Mass && PC->DeprojectMousePositionToWorld(Start, Direction))
    {
        const FVector End = Start + Direction * 100000.f;
        float EntityTime = 1.f;
        const int32 Id = Mass->Sweep(Start, End, 0.f, EntityTime);
        FHitResult Wall;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(PureMassCursor), false, Info->AvatarActor.Get());
        const bool bWall = GetWorld()->LineTraceSingleByChannel(Wall, Start, End, ECC_Visibility, Query);
        if (Id != INDEX_NONE && APureMassRuntime::EntityBeforeWall(EntityTime, bWall, Wall.Time))
        {
            Hit->HitResult.bBlockingHit = true;
            Hit->HitResult.Item = Id;
            Hit->HitResult.ImpactPoint = FMath::Lerp(Start, End, EntityTime);
            Hit->HitResult.Location = Hit->HitResult.ImpactPoint;
        }
        else if (bWall)
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
