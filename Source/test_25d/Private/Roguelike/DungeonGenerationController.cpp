#include "Roguelike/DungeonGenerationController.h"
#include "Roguelike/DungeonGenerationRuntime.h"
#include "EngineUtils.h"

namespace
{
ADungeonGenerationRuntime* FindDungeon(UWorld* World)
{
    if (World) for (TActorIterator<ADungeonGenerationRuntime> It(World); It; ++It) return *It;
    return nullptr;
}
}

void ADungeonGenerationController::PlayerTick(float DeltaTime)
{
    if (IsLocalController())
    {
        auto* Dungeon = FindDungeon(GetWorld());
        const bool Hold = !Dungeon || !Dungeon->CanLocalPlayerMove();
        if (Hold != bHoldingMovement) { SetIgnoreMoveInput(Hold); bHoldingMovement = Hold; }
        if (Dungeon && Dungeon->Manifest.GenerationId.IsValid())
        {
            const auto Generation = Dungeon->Manifest.GenerationId;
            if (!Dungeon->GetLocalFailure().IsEmpty() && FailedGeneration != Generation)
            {
                FailedGeneration = Generation; ServerReportDungeonFailure(Generation, Dungeon->GetLocalFailure().Left(200));
            }
            else if (Dungeon->IsLocalReady() && ReportedGeneration != Generation)
            {
                ReportedGeneration = Generation; ServerReportDungeonReady(Generation, Dungeon->Manifest.Digest);
            }
        }
    }
    Super::PlayerTick(DeltaTime);
}

void ADungeonGenerationController::ServerReportDungeonReady_Implementation(FGuid Generation, const FString& Digest)
{
    if (auto* Dungeon = FindDungeon(GetWorld())) Dungeon->ReportReady(this, Generation, Digest);
}

void ADungeonGenerationController::ServerReportDungeonFailure_Implementation(FGuid Generation, const FString& Reason)
{
    if (auto* Dungeon = FindDungeon(GetWorld())) Dungeon->ReportFailure(this, Generation, Reason.Left(200));
}

void ADungeonGenerationController::EndPlay(EEndPlayReason::Type Reason)
{
    if (bHoldingMovement) { SetIgnoreMoveInput(false); bHoldingMovement = false; }
    Super::EndPlay(Reason);
}
