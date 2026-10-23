#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Engine/NetSerialization.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Net/Serialization/FastArraySerializer.h"
#include "PureMass/PureMassTypes.h"
#include "PureMassCrowd.generated.h"

class APureMassCrowd;
class UAnimBank;
class UAnimSequenceTransformProviderDataInstance;

/** Wire state only. There is no replicated Actor or component for an individual enemy. */
USTRUCT()
struct FPureMassNetEntity : public FFastArraySerializerItem
{
    GENERATED_BODY()
    UPROPERTY() int32 Id = INDEX_NONE;
    UPROPERTY() FVector_NetQuantize10 Location = FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantize10 Velocity = FVector::ZeroVector;
    UPROPERTY() float Health = 0.f;
    UPROPERTY() float MaxHealth = 0.f;
    UPROPERTY() uint8 State = 0;
    UPROPERTY() TObjectPtr<UPureMassMonsterType> Type;

    FPureMassView ToView() const;
    bool SetFromView(const FPureMassView& View);
};

USTRUCT()
struct FPureMassNetEntities : public FFastArraySerializer
{
    GENERATED_BODY()
    UPROPERTY() TArray<FPureMassNetEntity> Items;
    TWeakObjectPtr<APureMassCrowd> Owner;

    bool NetDeltaSerialize(FNetDeltaSerializeInfo& DeltaParams)
    {
        return FastArrayDeltaSerialize<FPureMassNetEntity, FPureMassNetEntities>(Items, DeltaParams, *this);
    }
    void PostReplicatedReceive(const FFastArraySerializer::FPostReplicatedReceiveParameters& Parameters);
};

template<> struct TStructOpsTypeTraits<FPureMassNetEntities> : TStructOpsTypeTraitsBase2<FPureMassNetEntities>
{
    enum { WithNetDeltaSerializer = true };
};

USTRUCT()
struct FPureMassRenderBatch
{
    GENERATED_BODY()
    UPROPERTY(Transient) TObjectPtr<UPureMassMonsterType> Type;
    UPROPERTY(Transient) TObjectPtr<UInstancedSkinnedMeshComponent> Component;
    UPROPERTY(Transient) TObjectPtr<UAnimSequenceTransformProviderDataInstance> Playback;
};

struct FPureMassRenderInstance
{
    FPrimitiveInstanceId Instance;
    int32 BatchIndex = INDEX_NONE;
    int32 Track = INDEX_NONE;
    uint8 State = 255;
    FVector DisplayLocation = FVector::ZeroVector;
    FVector StartLocation = FVector::ZeroVector;
    FVector TargetLocation = FVector::ZeroVector;
    FQuat Facing = FQuat::Identity;
    float InterpolationAge = 0.f;
};

/** The only crowd Actor: shared replication plus one GPU skinned component per type. */
UCLASS()
class TEST_25D_API APureMassCrowd : public AActor
{
    GENERATED_BODY()
public:
    APureMassCrowd();
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UFUNCTION(BlueprintPure, Category="PureMass|Diagnostics") int32 GetRenderedInstanceCount() const;
    UFUNCTION(BlueprintPure, Category="PureMass|Diagnostics") int32 GetReplicatedEntityCount() const;
    UFUNCTION(BlueprintPure, Category="PureMass|Diagnostics") int32 GetRenderComponentCount() const;
    UFUNCTION(BlueprintPure, Category="PureMass|Diagnostics") int32 GetAnimationTrackCount() const;

    /** Editor-only operation; refuses banks outside the new /Game/PureMass asset tree. */
    UFUNCTION(BlueprintCallable, Category="PureMass|Authoring", meta=(DevelopmentOnly))
    static UAnimSequenceTransformProviderData* CreateAnimationProvider(UAnimBank* Bank);

    void ApplyReplicatedSnapshot();

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    void PublishSnapshots(const TArray<FPureMassView>& Views);
    void ReconcileInstances(const TArray<FPureMassView>& Views);
    void UpdateTransforms(float DeltaSeconds);
    int32 FindOrCreateBatch(UPureMassMonsterType* Type);
    void RemoveRenderInstance(FPureMassRenderInstance& Instance);
    void SetAnimation(FPureMassRenderInstance& Instance, uint8 State);

    UPROPERTY(Replicated) FPureMassNetEntities NetEntities;
    UPROPERTY(Transient) TArray<FPureMassRenderBatch> RenderBatches;
    TMap<int32, FPureMassRenderInstance> RenderInstances;
    TSet<TWeakObjectPtr<UPureMassMonsterType>> RejectedTypes;
    float TimeUntilPublish = 0.f;
    static constexpr float SnapshotInterval = 0.1f;
};
