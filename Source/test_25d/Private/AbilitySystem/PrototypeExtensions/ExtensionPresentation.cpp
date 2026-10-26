#include "AbilitySystem/PrototypeExtensions/ExtensionPresentation.h"
#include "Components/TextRenderComponent.h"
#include "Components/SceneComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"
AExtensionPresentation::AExtensionPresentation()
{
    bReplicates=true; bAlwaysRelevant=true; SetNetUpdateFrequency(15);
    PrimaryActorTick.bCanEverTick=true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    SetActorEnableCollision(false);
}
void AExtensionPresentation::Refresh()
{
    if (GetNetMode()==NM_DedicatedServer) return;
    while (Labels.Num()<Marks.Num() && Labels.Num()<256)
    {
        auto* Label=NewObject<UTextRenderComponent>(this); Label->SetupAttachment(RootComponent);
        Label->SetHorizontalAlignment(EHTA_Center); Label->SetWorldSize(26); Label->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Label->RegisterComponent(); Labels.Add(Label);
    }
    for (int32 I=0;I<Labels.Num();++I)
    {
        Labels[I]->SetVisibility(Marks.IsValidIndex(I));
        if (!Marks.IsValidIndex(I)) continue;
        const auto& M=Marks[I]; Labels[I]->SetWorldLocation(M.Position);
        Labels[I]->SetText(FText::FromString(FString::Printf(TEXT("%d%s"),M.Layers,M.bPending?TEXT("!"):TEXT(""))));
        Labels[I]->SetTextRenderColor(M.bPending?FColor::Red:FColor::Yellow);
    }
}
void AExtensionPresentation::Tick(float Delta)
{
    Super::Tick(Delta);
    auto* PC=GetWorld()->GetFirstPlayerController();
    if (PC && PC->PlayerCameraManager) for (const auto& Label:Labels)
        if (Label->IsVisible()) Label->SetWorldRotation((PC->PlayerCameraManager->GetCameraLocation()-Label->GetComponentLocation()).Rotation());
}
void AExtensionPresentation::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{ Super::GetLifetimeReplicatedProps(OutLifetimeProps); DOREPLIFETIME(AExtensionPresentation,Marks); }
