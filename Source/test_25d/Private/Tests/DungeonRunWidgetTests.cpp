#include "Misc/AutomationTest.h"
#include "Roguelike/DungeonRunWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Engine/World.h"
#include "Input/Events.h"
#include "Widgets/SWidget.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDungeonPanelMouseTest, "test_25d.Roguelike.UI.PanelConsumesDisabledOfferClick",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDungeonPanelMouseTest::RunTest(const FString&)
{
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    auto* Widget = NewObject<UDungeonRunWidget>(World);
    Widget->Initialize();
    auto RootSlate = Widget->TakeWidget();
    UBorder* Panel = nullptr;
    UButton* Offer = nullptr;
    Widget->WidgetTree->ForEachWidget([&](UWidget* Child)
    {
        if (auto* Border = Cast<UBorder>(Child)) Panel = Border;
        if (!Offer) Offer = Cast<UButton>(Child);
    });
    if (TestNotNull(TEXT("Run panel exists"), Panel) && TestNotNull(TEXT("Offer exists"), Offer))
    {
        // A disabled Slate button leaves the event unhandled. Its visible parent
        // must consume that bubble instead of forwarding a world move/attack.
        Offer->SetIsEnabled(false);
        const FPointerEvent Mouse(0, FVector2D(10, 10), FVector2D(10, 10),
            TSet<FKey>{EKeys::LeftMouseButton}, EKeys::LeftMouseButton, 0.f, FModifierKeysState());
        TestFalse(TEXT("Disabled offer itself does not consume the press"),
            Offer->TakeWidget()->OnMouseButtonDown(FGeometry(), Mouse).IsEventHandled());
        TestEqual(TEXT("Panel participates in hit testing"), Panel->GetVisibility(), ESlateVisibility::Visible);
        TestTrue(TEXT("Panel consumes the unhandled press"),
            Panel->TakeWidget()->OnMouseButtonDown(FGeometry(), Mouse).IsEventHandled());
        TestTrue(TEXT("Panel consumes release too"),
            Panel->TakeWidget()->OnMouseButtonUp(FGeometry(), Mouse).IsEventHandled());
        TestEqual(TEXT("Outside panel remains available to gameplay"),
            Widget->WidgetTree->RootWidget->GetVisibility(), ESlateVisibility::SelfHitTestInvisible);
    }
    Widget->ReleaseSlateResources(true);
    World->DestroyWorld(false);
    return true;
}
#endif
