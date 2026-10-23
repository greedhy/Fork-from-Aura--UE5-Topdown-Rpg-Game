#include "UI/Widget/PrototypeSpellTree.h"
#include "UI/WidgetController/SpellMenuWidgetController.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Button.h"
#include "Components/TextBlock.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBox.h"
#include "Components/HorizontalBox.h"
#include "Components/UniformGridPanel.h"
#include "Components/UniformGridSlot.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/ScrollBox.h"
#include "AbilitySystem/Data/AbilityInfo.h"
#include "AbilitySystem/Prototypes/PrototypeAbility.h"
#include "AbilitySystem/Prototypes/AbilityPrototype.h"

void UPrototypeSpellEntry::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    auto* Button = WidgetTree->ConstructWidget<UButton>();
    auto* Text = WidgetTree->ConstructWidget<UTextBlock>();
    Text->SetText(Label);
    FSlateFontInfo Font = Text->GetFont(); Font.Size = 14; Text->SetFont(Font);
    Button->AddChild(Text);
    Button->OnClicked.AddDynamic(this, &ThisClass::Select);
    WidgetTree->RootWidget = Button;
}
void UPrototypeSpellEntry::Select()
{
    if (Tree)
        if (auto* Controller = Cast<USpellMenuWidgetController>(Tree->WidgetController)) Controller->SpellGlobeSelected(AbilityTag);
}
void UPrototypeSpellTree::NativeConstruct()
{
    Super::NativeConstruct();
    if (PrototypePage) return;
    auto* Root = Cast<USizeBox>(GetWidgetFromName(TEXT("SizeBox_Root")));
    if (!Root || !Root->GetContent()) return;
    OriginalPage = Root->GetContent();
    OriginalPage->RemoveFromParent();
    auto* Pages = WidgetTree->ConstructWidget<UVerticalBox>();
    Root->AddChild(Pages);
    auto* Tabs = WidgetTree->ConstructWidget<UHorizontalBox>();
    Pages->AddChildToVerticalBox(Tabs)->SetPadding(FMargin(0,0,0,8));
    auto* OriginalButton = WidgetTree->ConstructWidget<UButton>();
    auto* PrototypeButton = WidgetTree->ConstructWidget<UButton>();
    auto* OriginalText = WidgetTree->ConstructWidget<UTextBlock>();
    auto* PrototypeText = WidgetTree->ConstructWidget<UTextBlock>();
    OriginalText->SetText(FText::FromString(TEXT("  Skills  ")));
    PrototypeText->SetText(FText::FromString(TEXT("  Prototypes  ")));
    for (auto* Text : {OriginalText, PrototypeText}) { FSlateFontInfo Font = Text->GetFont(); Font.Size = 14; Text->SetFont(Font); }
    OriginalButton->AddChild(OriginalText); PrototypeButton->AddChild(PrototypeText);
    OriginalButton->OnClicked.AddDynamic(this, &ThisClass::ShowOriginal);
    PrototypeButton->OnClicked.AddDynamic(this, &ThisClass::ShowPrototypes);
    Tabs->AddChild(OriginalButton); Tabs->AddChild(PrototypeButton);
    Pages->AddChild(OriginalPage);
    auto* Grid = WidgetTree->ConstructWidget<UUniformGridPanel>();
    Grid->SetMinDesiredSlotHeight(42.f); Grid->SetSlotPadding(FMargin(3.f));
    auto* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    auto* Bounds = WidgetTree->ConstructWidget<USizeBox>();
    Bounds->SetHeightOverride(215.f); Bounds->AddChild(Scroll); Scroll->AddChild(Grid);
    PrototypePage = Bounds;
    Pages->AddChild(Bounds);
    const auto* Catalog = LoadObject<UAbilityInfo>(nullptr,TEXT("/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo.DA_AbilityInfo"));
    int32 Index = 0;
    if (Catalog) for (const auto& Row : Catalog->AbilityInformation)
    {
        const auto* GA = Row.Ability ? Cast<UPrototypeAbility>(Row.Ability->GetDefaultObject()) : nullptr;
        if (!GA || !GA->Prototype) continue;
        // NewObject + Initialize lets us supply the label before NativeOnInitialized builds its button.
        auto* Entry = NewObject<UPrototypeSpellEntry>(this);
        Entry->Tree = this; Entry->Label = GA->Prototype->DisplayName;
        Entry->AbilityTag = Row.AbilityTag;
        Entry->Initialize();
        Grid->AddChildToUniformGrid(Entry, Index / 2, Index % 2);
        ++Index;
    }
    ShowOriginal();
}
void UPrototypeSpellTree::ShowOriginal()
{
    if (auto* Controller = Cast<USpellMenuWidgetController>(WidgetController)) Controller->GlobeDeselect();
    if (OriginalPage) OriginalPage->SetVisibility(ESlateVisibility::Visible);
    if (PrototypePage) PrototypePage->SetVisibility(ESlateVisibility::Collapsed);
}
void UPrototypeSpellTree::ShowPrototypes()
{
    if (auto* Controller = Cast<USpellMenuWidgetController>(WidgetController)) Controller->GlobeDeselect();
    if (OriginalPage) OriginalPage->SetVisibility(ESlateVisibility::Collapsed);
    if (PrototypePage) PrototypePage->SetVisibility(ESlateVisibility::Visible);
}
