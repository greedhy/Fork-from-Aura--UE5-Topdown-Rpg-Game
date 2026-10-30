#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Roguelike/DungeonGenerationTypes.h"
#include "DungeonGenerationRuntime.generated.h"

class UDungeonGenerationProfile;
class ULevelStreamingDynamic;
class UStaticMeshComponent;
class ADungeonGenerationController;

UENUM(BlueprintType)
enum class EDungeonGenerationPhase : uint8 { Pending, Loading, WaitingForPlayers, Ready, Failed };

USTRUCT(BlueprintType)
struct FDungeonGenerationManifest
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FGuid GenerationId;
    UPROPERTY(BlueprintReadOnly) FDungeonLayout Layout;
    UPROPERTY(BlueprintReadOnly) FString Digest;
    UPROPERTY(BlueprintReadOnly) float RoomSpacing = 2400.f;
    UPROPERTY(BlueprintReadOnly) int32 ExpectedPlayers = 1;
};

/** Authority-owned assembly host. Place exactly once at the persistent entrance origin. */
UCLASS()
class TEST_25D_API ADungeonGenerationRuntime : public AActor
{
    GENERATED_BODY()
public:
    ADungeonGenerationRuntime();
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dungeon") TObjectPtr<UDungeonGenerationProfile> Profile;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dungeon") int32 Seed = 42;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Dungeon", meta=(ClampMin="1", ClampMax="2")) int32 ExpectedPlayers = 1;
    UPROPERTY(ReplicatedUsing=OnRep_Manifest, BlueprintReadOnly, Category="Dungeon") FDungeonGenerationManifest Manifest;
    UPROPERTY(Replicated, BlueprintReadOnly, Category="Dungeon") EDungeonGenerationPhase Phase = EDungeonGenerationPhase::Pending;
    UPROPERTY(Replicated, BlueprintReadOnly, Category="Dungeon") FString FailureReason;
    UPROPERTY(Replicated, BlueprintReadOnly, Category="Dungeon") int32 ReadyPlayers = 0;
    UFUNCTION(BlueprintPure, Category="Dungeon") FString GetGenerationReport() const;
    UFUNCTION(BlueprintPure, Category="Dungeon") bool IsLocalReady() const { return bLocalReady; }
    bool CanLocalPlayerMove() const { return bLocalReady && Phase == EDungeonGenerationPhase::Ready && LocalFailure.IsEmpty(); }
    const FString& GetLocalFailure() const { return LocalFailure; }
    void ReportReady(ADungeonGenerationController* Controller, FGuid Generation, const FString& Digest);
    void ReportFailure(ADungeonGenerationController* Controller, FGuid Generation, const FString& Reason);
protected:
    virtual void BeginPlay() override;
private:
    UFUNCTION() void OnRep_Manifest();
    void StartLocalAssembly();
    void CreateDoorBarriers();
    bool CheckNavigation(FString& Reason) const;
    void Fail(const FString& Reason);
    FVector RoomCenter(int32 Index) const;
    bool IsCurrentController(const ADungeonGenerationController* Controller) const;
    UPROPERTY(Transient) TArray<TObjectPtr<ULevelStreamingDynamic>> StreamingRooms;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> DoorBarriers;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> SafetyGate;
    FGuid AssembledGeneration;
    FDungeonReadyBarrier Barrier;
    double StartedAt = 0;
    double GenerationMilliseconds = 0;
    bool bLocalReady = false;
    FString LocalFailure;
    FString PendingReason;
};
