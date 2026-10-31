#include "Misc/AutomationTest.h"
#include "Character/ShamanEnemyCharacter.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "UObject/Script.h"
#include "AIController.h"
#include "Roguelike/DungeonRunDirector.h"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShamanSummonConfigTest,"test_25d.Shaman.SummonConfigBounds",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShamanSummonConfigTest::RunTest(const FString&)
{
    auto* Config=NewObject<UShamanSummonConfig>();
    TestFalse(TEXT("Missing class rejected"),Config->ValidateSummon());
    Config->MinionClass=AEnemyCharacter::StaticClass();
    TestTrue(TEXT("Existing five-minion defaults valid"),Config->ValidateSummon());
    Config->PerCast=1;TestTrue(TEXT("One minion does not require spread division"),Config->ValidateSummon());
    Config->MaxAlive=6;TestFalse(TEXT("Unbounded swarm rejected"),Config->ValidateSummon());
    Config->MaxAlive=5;Config->MinionClass=AShamanEnemyCharacter::StaticClass();
    TestFalse(TEXT("Recursive summoners rejected"),Config->ValidateSummon());return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShamanLeaseTest,"test_25d.Shaman.StaleSummonLease",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShamanLeaseTest::RunTest(const FString&)
{
    FEditorScriptExecutionGuard Guard;
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    auto* Actor=World->SpawnActor<AShamanEnemyCharacter>();
    auto* Config=NewObject<UShamanSummonConfig>();Config->MinionClass=AEnemyCharacter::StaticClass();
    TestEqual(TEXT("A callback from another lease cannot spawn"),Actor->Summon(Config,Actor->GetDungeonPoolLease()+1),0);
    TestEqual(TEXT("No ownership recorded for stale callback"),Actor->GetOwnedMinionCount(),0);
    GEngine->DestroyWorldContext(World);World->DestroyWorld(false);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FShamanPossessionTest,"test_25d.Shaman.PossessedSummonRetirement",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FShamanPossessionTest::RunTest(const FString&)
{
    FEditorScriptExecutionGuard Guard;
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    auto* Source=World->SpawnActor<AShamanEnemyCharacter>();
    auto* Minion=World->SpawnActor<AEnemyCharacter>();
    auto* Controller=World->SpawnActor<AAIController>();
    auto* Director=World->SpawnActor<ADungeonRunDirector>();
    Minion->SummoningSource=Source;Minion->SetOwner(Source);
    Minion->Tags.AddUnique(TEXT("SourceOwnedSummon"));
    Controller->Possess(Minion);
    TestTrue(TEXT("Possession replaces pawn Owner"),Minion->GetOwner()==Controller);
    TestTrue(TEXT("Summon provenance survives possession"),Minion->SummoningSource.Get()==Source);
    Director->RetireSummonedEnemy(Source,Minion);
    TestTrue(TEXT("Source can retire possessed summon"),Minion->IsActorBeingDestroyed());
    GEngine->DestroyWorldContext(World);World->DestroyWorld(false);return true;
}
#endif
