#include "Roguelike/DungeonPlayerCharacter.h"
#include "Roguelike/DungeonRunDirector.h"
#include "AbilitySystem/Ability/MyPassiveAbility.h"
#include "AbilitySystem/MyAttributeSet.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Player/MyPlayerState.h"
#include "Terrain/TerrainStatusComponent.h"
#include "MyGameplayTags.h"
#include "TimerManager.h"
#include "Net/UnrealNetwork.h"

namespace
{
FGameplayTagContainer DungeonDownedInputTags()
{
    const auto& Tags = FMyGameplayTags::Get();
    FGameplayTagContainer Result;
    Result.AddTag(Tags.Player_Block_InputPressed);
    Result.AddTag(Tags.Player_Block_InputHeld);
    Result.AddTag(Tags.Player_Block_InputReleased);
    Result.AddTag(Tags.Player_Block_CursorTrace);
    return Result;
}
bool IsDungeonPassive(const FGameplayAbilitySpec& Spec)
{
    const auto* Ability = Cast<UMyGameplayAbility>(Spec.Ability);
    if (Ability && Ability->IsInputToggleAbility()) return false;
    return Spec.Ability && (Spec.Ability->IsA<UMyPassiveAbility>() ||
        Spec.Ability->GetAssetTags().HasTag(FGameplayTag::RequestGameplayTag(TEXT("Abilities.Passive"))));
}
FGameplayTagContainer DungeonDownedAbilityTags()
{
    return FGameplayTagContainer(FGameplayTag::RequestGameplayTag(TEXT("Abilities")));
}
void ClearDungeonDebuffs(UAbilitySystemComponent* ASC)
{
    if (!ASC) return;
    // Preserve attribute initialization, beneficial buffs and cooldowns; only project debuffs expire on down.
    const FGameplayTagContainer Debuffs(FGameplayTag::RequestGameplayTag(TEXT("Debuff")));
    ASC->RemoveActiveEffects(FGameplayEffectQuery::MakeQuery_MatchAnyOwningTags(Debuffs));
}
}

void ADungeonPlayerCharacter::Die(const FVector& DeathImpulse)
{
    if (!HasAuthority() || GetNetMode() == NM_Client || bDungeonDowned || bDead) return;
    PausedPassiveAbilities.Reset();
    if (AbilitySystemComponent)
    {
        FScopedAbilityListLock Lock(*AbilitySystemComponent);
        for (const auto& Spec : AbilitySystemComponent->GetActivatableAbilities())
            if (Spec.IsActive() && IsDungeonPassive(Spec)) PausedPassiveAbilities.Add(Spec.Handle);
    }
    // Never enter either inherited death path: both permanently dismantle the pawn or its loadout.
    GetWorldTimerManager().ClearTimer(DeathTimer);
    bDungeonDowned = true;
    OnRep_Downed();
    ForceNetUpdate();
    if (auto* Director = ADungeonRunDirector::Find(GetWorld())) Director->NotifyPlayerDown(this);
}

bool ADungeonPlayerCharacter::ReviveForDungeon(FVector SafeLocation, float Fraction)
{
    if (!HasAuthority() || GetNetMode() == NM_Client || !bDungeonDowned || !FMath::IsFinite(Fraction) ||
        Fraction <= 0.f || Fraction > 1.f || SafeLocation.ContainsNaN()) return false;
    auto* State = GetPlayerState<AMyPlayerState>();
    auto* ASC = GetAbilitySystemComponent();
    if (!State || !ASC || ASC != State->GetAbilitySystemComponent() ||
        ASC->GetOwnerActor() != State || ASC->GetAvatarActor() != this) return false;
    const float MaxHealth = ASC->GetNumericAttribute(UMyAttributeSet::GetMaxHealthAttribute());
    const float MaxMana = ASC->GetNumericAttribute(UMyAttributeSet::GetMaxManaAttribute());
    if (!FMath::IsFinite(MaxHealth) || MaxHealth <= 0.f || !FMath::IsFinite(MaxMana) || MaxMana < 0.f) return false;
    if (!SetActorLocation(SafeLocation, false, nullptr, ETeleportType::TeleportPhysics)) return false;
    // A fatal hit can add its debuff after Die returns. Also discard any instant/periodic
    // IncomingDamage left by the shared AttributeSet's dead-target early return, while still dead.
    ClearDungeonDebuffs(ASC);
    ASC->SetNumericAttributeBase(UMyAttributeSet::GetIncomingDamageAttribute(), 0.f);
    ASC->SetNumericAttributeBase(UMyAttributeSet::GetHealthAttribute(), FMath::Clamp(MaxHealth * Fraction, 0.f, MaxHealth));
    ASC->SetNumericAttributeBase(UMyAttributeSet::GetManaAttribute(), FMath::Clamp(MaxMana * Fraction, 0.f, MaxMana));
    bDungeonDowned = false;
    OnRep_Downed();
    const auto Resume = MoveTemp(PausedPassiveAbilities);
    for (const auto Handle : Resume)
        if (const auto* Spec = ASC->FindAbilitySpecFromHandle(Handle); Spec && IsDungeonPassive(*Spec) && !Spec->IsActive() &&
            Spec->DynamicAbilityTags.HasTagExact(FMyGameplayTags::Get().Abilities_Status_Equipped))
            ASC->TryActivateAbility(Handle);
    ForceNetUpdate();
    return true;
}

void ADungeonPlayerCharacter::UpdateDownedInputBlock()
{
    UAbilitySystemComponent* Desired = bDungeonDowned ? AbilitySystemComponent.Get() : nullptr;
    if (DownedInputASC.Get() == Desired) return;
    if (auto* Previous = DownedInputASC.Get())
    {
        Previous->RemoveLooseGameplayTags(DungeonDownedInputTags());
        Previous->UnBlockAbilitiesWithTags(DungeonDownedAbilityTags());
    }
    DownedInputASC = Desired;
    if (Desired)
    {
        Desired->AddLooseGameplayTags(DungeonDownedInputTags());
        // Equip/UI RPCs and direct GAS activation must obey the same downed gate as keyboard input.
        Desired->BlockAbilitiesWithTags(DungeonDownedAbilityTags());
    }
}

void ADungeonPlayerCharacter::OnRep_Downed()
{
    bDead = bDungeonDowned;
    UpdateDownedInputBlock();
    if (bAppliedDowned == bDungeonDowned) return;
    bAppliedDowned = bDungeonDowned;
    if (bDungeonDowned)
    {
        LivingCapsuleCollision = GetCapsuleComponent()->GetCollisionEnabled();
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        GetCharacterMovement()->StopMovementImmediately();
        GetCharacterMovement()->DisableMovement();
        if (AbilitySystemComponent) AbilitySystemComponent->CancelAllAbilities();
        if (TerrainStatus) TerrainStatus->ClearTerrainEffects();
        if (HasAuthority()) ClearDungeonDebuffs(AbilitySystemComponent);
    }
    else
    {
        GetCapsuleComponent()->SetCollisionEnabled(LivingCapsuleCollision);
        GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        RefreshMovementSpeed();
    }
    GetMesh()->SetVisibility(!bDungeonDowned, true);
    if (Weapon) Weapon->SetVisibility(!bDungeonDowned, true);
    if (bDungeonDowned) FOnDeath.Broadcast(this);
}

void ADungeonPlayerCharacter::InitAbilityActorInfo()
{
    Super::InitAbilityActorInfo();
    // Downed replication can arrive before the owning PlayerState/ASC.
    UpdateDownedInputBlock();
    if (bDungeonDowned && AbilitySystemComponent) AbilitySystemComponent->CancelAllAbilities();
}

void ADungeonPlayerCharacter::EndPlay(EEndPlayReason::Type Reason)
{
    if (auto* ASC = DownedInputASC.Get())
    {
        ASC->RemoveLooseGameplayTags(DungeonDownedInputTags());
        ASC->UnBlockAbilitiesWithTags(DungeonDownedAbilityTags());
    }
    DownedInputASC.Reset();
    Super::EndPlay(Reason);
}
void ADungeonPlayerCharacter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ADungeonPlayerCharacter, bDungeonDowned);
}
