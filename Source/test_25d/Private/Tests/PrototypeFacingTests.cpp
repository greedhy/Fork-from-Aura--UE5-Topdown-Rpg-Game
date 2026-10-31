#include "Misc/AutomationTest.h"
#include "AbilitySystem/Prototypes/PrototypeFacing.h"
#include "Roguelike/DungeonPlayerCharacter.h"
#include "Engine/Engine.h"
#include "Engine/World.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FPrototypeFacingTest, "test_25d.Abilities.PrototypeFacing",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FPrototypeFacingTest::RunTest(const FString& Parameters)
{
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    auto* Player = World->SpawnActor<ADungeonPlayerCharacter>();
    const FVector Origin = Player->GetActorLocation();
    PrototypeFacing::Apply(Player, Origin + FVector(0, 500, 200), false);
    TestTrue(TEXT("Room player faces aimed cast"), FMath::IsNearlyEqual(Player->GetActorRotation().Yaw, 90.f));
    TestTrue(TEXT("Cast does not tilt player"), FMath::IsNearlyZero(Player->GetActorRotation().Pitch));
    PrototypeFacing::Apply(Player, Origin + FVector(-500, 0, 0), true);
    TestTrue(TEXT("Self cast preserves facing"), FMath::IsNearlyEqual(Player->GetActorRotation().Yaw, 90.f));
    PrototypeFacing::Apply(Player, Origin + FVector(0, 0, 200), false);
    TestTrue(TEXT("Vertical target preserves facing"), FMath::IsNearlyEqual(Player->GetActorRotation().Yaw, 90.f));
    auto* Other = World->SpawnActor<AActor>();
    PrototypeFacing::Apply(Other, Other->GetActorLocation() + FVector(0, 500, 0), false);
    TestTrue(TEXT("Does not override non-player AI facing"), FMath::IsNearlyZero(Other->GetActorRotation().Yaw));
    GEngine->DestroyWorldContext(World);
    World->DestroyWorld(false);
    return true;
}
#endif
