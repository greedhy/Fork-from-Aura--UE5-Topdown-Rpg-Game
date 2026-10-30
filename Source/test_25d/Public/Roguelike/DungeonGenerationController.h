#pragma once

#include "CoreMinimal.h"
#include "PureMass/PureMassPlayerController.h"
#include "DungeonGenerationController.generated.h"

/** Copied blueprint retains existing movement, GAS and UI configuration. */
UCLASS()
class TEST_25D_API ADungeonGenerationController : public APureMassPlayerController
{
    GENERATED_BODY()
public:
    virtual void PlayerTick(float DeltaTime) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    UFUNCTION(Server, Reliable) void ServerReportDungeonReady(FGuid Generation, const FString& Digest);
    UFUNCTION(Server, Reliable) void ServerReportDungeonFailure(FGuid Generation, const FString& Reason);
private:
    bool bHoldingMovement = false;
    FGuid ReportedGeneration;
    FGuid FailedGeneration;
};
