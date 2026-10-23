#include "Terrain/TerrainStatusComponent.h"
#include "Terrain/TerrainSurface.h"
#include "Terrain/TerrainStatusEffects.h"
#include "AbilitySystemComponent.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "Character/BaseCharacter.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NiagaraComponent.h"
#include "Net/UnrealNetwork.h"

UTerrainStatusComponent::UTerrainStatusComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickInterval = .1f;
    Presentation.Systems.SetNum(4);
}

bool UTerrainStatusComponent::IsTerrainStatusActive(ETerrainSurfaceType Type) const
{
    return (Presentation.ActiveMask & (1 << static_cast<uint8>(Type))) != 0;
}

void UTerrainStatusComponent::RefreshContact(ATerrainSurface* Surface)
{
    auto* Character = Cast<ABaseCharacter>(GetOwner());
    if (!Character || !Character->HasAuthority() || !IsValid(Surface) || !Surface->CanAffectCharacter(Character)) return;
    FContact* Contact = Contacts.FindByPredicate([Surface](const FContact& Item) { return Item.Surface == Surface; });
    if (!Contact) Contact = &Contacts.AddDefaulted_GetRef();
    Contact->Surface = Surface;
    Contact->Config = Surface->Config;
    // One scan interval of grace prevents flicker at adjoining tile boundaries.
    Contact->Remaining = .3f + (Surface->Config->SurfaceType == ETerrainSurfaceType::Vines ? 0.f : FMath::Max(0.f, Surface->Config->ExitDuration));
    UpdateEffects();
}

void UTerrainStatusComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaTime, TickType, TickFunction);
    auto* Character = Cast<ABaseCharacter>(GetOwner());
    if (!Character) return;
    if (Character->IsDead_Implementation())
    {
        ClearTerrainEffects();
        return;
    }
    if (!Character->HasAuthority()) return;
    RootRemaining = FMath::Max(0.f, RootRemaining - DeltaTime);
    RecoveryRemaining = FMath::Max(0.f, RecoveryRemaining - DeltaTime);
    for (FContact& Contact : Contacts) Contact.Remaining -= DeltaTime;
    Contacts.RemoveAll([](const FContact& Contact) { return Contact.Remaining <= 0.f || !Contact.Surface.IsValid() || !Contact.Config.IsValid() || !Contact.Surface->bEnabled; });
    UpdateEffects();
}

void UTerrainStatusComponent::UpdateEffects()
{
    auto* Character = Cast<ABaseCharacter>(GetOwner());
    UAbilitySystemComponent* ASC = Character ? Character->GetAbilitySystemComponent() : nullptr;
    if (!ASC || !Character->HasAuthority()) return;
    if (EffectASC.IsValid() && EffectASC != ASC) ClearTerrainEffects();
    EffectASC = ASC;
    const FContact* Best[4] = {};
    for (const FContact& Contact : Contacts)
    {
        if (!Contact.Config.IsValid() || !Contact.Surface.IsValid()) continue;
        const UTerrainSurfaceConfig* Config = Contact.Config.Get();
        const int32 Index = static_cast<uint8>(Config->SurfaceType);
        if (Index >= 4) continue;
        if (!Best[Index] || (Index == 1 ? Config->MovementMultiplier < Best[Index]->Config->MovementMultiplier
                                       : Config->DamagePerSecond > Best[Index]->Config->DamagePerSecond)) Best[Index] = &Contact;
    }
    if (Best[3] && RecoveryRemaining <= 0.f)
    {
        RootRemaining = FMath::Max(.1f, Best[3]->Config->EntangleDuration);
        RecoveryRemaining = RootRemaining + FMath::Max(.5f, Best[3]->Config->EntangleRecovery);
        RootSystem = Best[3]->Config->StatusVFX;
    }
    FTerrainStatusPresentation Next;
    Next.Systems.SetNum(4);
    Next.MovementMultiplier = Best[1] ? FMath::Clamp(Best[1]->Config->MovementMultiplier, .05f, 1.f) : 1.f;
    UClass* Classes[4] = { UTerrainBurnEffect::StaticClass(), UTerrainFrostEffect::StaticClass(), UTerrainPoisonEffect::StaticClass(), UTerrainEntangleEffect::StaticClass() };
    for (int32 Index = 0; Index < 4; ++Index)
    {
        const bool bActive = Index == 3 ? RootRemaining > 0.f : Best[Index] != nullptr;
        if (!bActive)
        {
            if (EffectHandles[Index].IsValid()) ASC->RemoveActiveGameplayEffect(EffectHandles[Index]);
            EffectHandles[Index].Invalidate();
            continue;
        }
        Next.ActiveMask |= (1 << Index);
        Next.Systems[Index] = Index == 3 ? RootSystem : Best[Index]->Config->StatusVFX;
        const float Damage = Best[Index] ? FMath::Max(0.f, Best[Index]->Config->DamagePerSecond) : 0.f;
        if (Best[Index])
        {
            // A stronger/remaining tile may belong to another caster. Update attribution
            // in place so switching the winning contact does not restart the periodic clock.
            if (const FActiveGameplayEffect* Active = ASC->GetActiveGameplayEffect(EffectHandles[Index]))
            {
                ATerrainSurface* Source = Best[Index]->Surface.Get();
                FGameplayEffectContextHandle Context = Active->Spec.GetContext();
                Context.AddInstigator(Source->bOnlyAffectCasterEnemies ? Source->GetOwner() : Source, Source);
            }
        }
        if (!EffectHandles[Index].IsValid() || !ASC->GetActiveGameplayEffect(EffectHandles[Index]))
        {
            ATerrainSurface* Source = Best[Index] ? Best[Index]->Surface.Get() : nullptr;
            AActor* Instigator = Source && Source->bOnlyAffectCasterEnemies ? Source->GetOwner() : Source;
            UAbilitySystemComponent* SourceASC = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Instigator);
            FGameplayEffectContextHandle Context = (SourceASC ? SourceASC : ASC)->MakeEffectContext();
            Context.AddInstigator(Instigator, Source);
            Context.AddSourceObject(this);
            FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(Classes[Index], 1.f, Context);
            if (Spec.IsValid())
            {
                if (Index == 0 || Index == 2) Spec.Data->SetSetByCallerMagnitude(TerrainTags::Damage, Damage);
                EffectHandles[Index] = ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
            }
        }
        else if (Index == 0 || Index == 2)
        {
            // Keep the existing periodic timer: continuous contact must not reset it.
            ASC->UpdateActiveGameplayEffectSetByCallerMagnitude(EffectHandles[Index], TerrainTags::Damage, Damage);
        }
    }
    const bool bChanged = Presentation.ActiveMask != Next.ActiveMask
        || !FMath::IsNearlyEqual(Presentation.MovementMultiplier, Next.MovementMultiplier)
        || Presentation.Systems != Next.Systems;
    Presentation = Next;
    if (bChanged)
    {
        UpdatePresentation();
        Character->ForceNetUpdate();
    }
}

void UTerrainStatusComponent::ClearTerrainEffects()
{
    Contacts.Reset();
    RootRemaining = RecoveryRemaining = 0.f;
    RootSystem = nullptr;
    if (GetOwner() && GetOwner()->HasAuthority())
    {
        if (UAbilitySystemComponent* ASC = EffectASC.Get())
            for (auto& Handle : EffectHandles)
                if (Handle.IsValid()) ASC->RemoveActiveGameplayEffect(Handle);
        for (auto& Handle : EffectHandles) Handle.Invalidate();
        EffectASC.Reset();
    }
    const bool bWasActive = Presentation.ActiveMask != 0;
    Presentation.ActiveMask = 0;
    Presentation.MovementMultiplier = 1.f;
    Presentation.Systems.SetNum(4);
    for (auto& System : Presentation.Systems) System = nullptr;
    UpdatePresentation();
    if (bWasActive && GetOwner() && GetOwner()->HasAuthority()) GetOwner()->ForceNetUpdate();
}

void UTerrainStatusComponent::OnRep_Presentation() { UpdatePresentation(); }

void UTerrainStatusComponent::UpdatePresentation()
{
    auto* Character = Cast<ABaseCharacter>(GetOwner());
    if (!Character) return;
    Character->RefreshMovementSpeed();
    if (GetNetMode() == NM_DedicatedServer) return;
    VisualComponents.SetNum(4);
    for (int32 Index = 0; Index < 4; ++Index)
    {
        UNiagaraSystem* System = Presentation.Systems.IsValidIndex(Index) ? Presentation.Systems[Index].Get() : nullptr;
        const bool bVisible = !Character->IsDead_Implementation() && (Presentation.ActiveMask & (1 << Index)) && System;
        UNiagaraComponent* Component = VisualComponents[Index];
        if (bVisible)
        {
            if (!Component)
            {
                Component = NewObject<UNiagaraComponent>(Character);
                Component->SetAutoActivate(false);
                Component->SetupAttachment(Character->GetRootComponent());
                Component->RegisterComponent();
                VisualComponents[Index] = Component;
            }
            const bool bChanged = Component->GetAsset() != System;
            if (bChanged) Component->SetAsset(System);
            Component->SetRelativeLocation(FVector(0,0,-Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+8));
            if (bChanged || !Component->IsActive()) Component->Activate(true);
        }
        else if (Component && Component->IsActive()) Component->DeactivateImmediate();
    }
}

void UTerrainStatusComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    ClearTerrainEffects();
    for (UNiagaraComponent* Component : VisualComponents) if (IsValid(Component)) Component->DestroyComponent();
    VisualComponents.Reset();
    Super::EndPlay(Reason);
}

void UTerrainStatusComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UTerrainStatusComponent, Presentation);
}
