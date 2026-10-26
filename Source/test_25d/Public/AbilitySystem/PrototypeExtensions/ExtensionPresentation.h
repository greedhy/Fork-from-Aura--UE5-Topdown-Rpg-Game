#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ExtensionPresentation.generated.h"

USTRUCT(BlueprintType)
struct FExtensionMarkView
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 Id = 0;
    UPROPERTY(BlueprintReadOnly) FVector Position;
    UPROPERTY(BlueprintReadOnly) int32 Layers = 0;
    UPROPERTY(BlueprintReadOnly) bool bPending = false;
};

/** One presentation actor per world, with capped pooled mark labels. */
UCLASS()
class TEST_25D_API AExtensionPresentation : public AActor
{
    GENERATED_BODY()
public:
    AExtensionPresentation();
    UPROPERTY(ReplicatedUsing=Refresh, BlueprintReadOnly) TArray<FExtensionMarkView> Marks;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UFUNCTION() void Refresh();
private:
    UPROPERTY() TArray<TObjectPtr<class UTextRenderComponent>> Labels;
};
