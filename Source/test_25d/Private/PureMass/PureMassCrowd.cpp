#include "PureMass/PureMassCrowd.h"
#include "PureMass/PureMassSubsystem.h"
#include "Animation/AnimBank.h"
#include "Animation/AnimSequenceTransformProviderData.h"
#include "Components/SceneComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Misc/PackageName.h"
#include "Net/UnrealNetwork.h"
#include "UObject/Package.h"

DEFINE_LOG_CATEGORY_STATIC(LogPureMassCrowd, Log, All);

namespace
{
    bool IsPureMassAsset(const UObject* Asset)
    {
        return Asset && Asset->GetOutermost()->GetName().StartsWith(TEXT("/Game/PureMass/"));
    }

    FVector QuantizeVector(const FVector& Vector)
    {
        return FVector(FMath::RoundToDouble(Vector.X * 10.0) * 0.1,
            FMath::RoundToDouble(Vector.Y * 10.0) * 0.1,
            FMath::RoundToDouble(Vector.Z * 10.0) * 0.1);
    }
}

FPureMassView FPureMassNetEntity::ToView() const
{
    FPureMassView View;
    View.Id = Id;
    View.Location = Location;
    View.Velocity = Velocity;
    View.Health = Health;
    View.MaxHealth = MaxHealth;
    View.State = State;
    View.Type = Type;
    return View;
}

bool FPureMassNetEntity::SetFromView(const FPureMassView& View)
{
    const FVector NewLocation = QuantizeVector(View.Location);
    const FVector NewVelocity = QuantizeVector(View.Velocity);
    const bool bChanged = Id != View.Id || Location != NewLocation || Velocity != NewVelocity
        || Health != View.Health || MaxHealth != View.MaxHealth || State != View.State || Type != View.Type;
    Id = View.Id;
    Location = NewLocation;
    Velocity = NewVelocity;
    Health = View.Health;
    MaxHealth = View.MaxHealth;
    State = View.State;
    Type = View.Type;
    return bChanged;
}

void FPureMassNetEntities::PostReplicatedReceive(const FFastArraySerializer::FPostReplicatedReceiveParameters& Parameters)
{
    // Also called when an initially unmapped type asset becomes available.
    if (APureMassCrowd* Crowd = Owner.Get()) Crowd->ApplyReplicatedSnapshot();
}

APureMassCrowd::APureMassCrowd()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostPhysics;
    bReplicates = true;
    bAlwaysRelevant = true;
    SetReplicateMovement(false);
    SetNetUpdateFrequency(10.f);
    SetMinNetUpdateFrequency(10.f);
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("CrowdRoot"));
    NetEntities.Owner = this;
}

void APureMassCrowd::BeginPlay()
{
    Super::BeginPlay();
    NetEntities.Owner = this;
    // Initial property replication can precede BeginPlay.
    if (!HasAuthority()) ApplyReplicatedSnapshot();
}

void APureMassCrowd::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(APureMassCrowd, NetEntities);
}

void APureMassCrowd::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (HasAuthority())
    {
        UPureMassSubsystem* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>();
        if (!Mass) return;
        TimeUntilPublish -= DeltaSeconds;
        // Dedicated servers only collect copies when a network update is due.
        if (GetNetMode() != NM_DedicatedServer || TimeUntilPublish <= 0.f)
        {
            const TArray<FPureMassView> Views = Mass->GetSnapshots();
            if (TimeUntilPublish <= 0.f)
            {
                PublishSnapshots(Views);
                TimeUntilPublish = SnapshotInterval;
            }
            if (GetNetMode() != NM_DedicatedServer) ReconcileInstances(Views);
        }
    }
    if (GetNetMode() != NM_DedicatedServer) UpdateTransforms(DeltaSeconds);
}

void APureMassCrowd::PublishSnapshots(const TArray<FPureMassView>& Views)
{
    TSet<int32> Living;
    Living.Reserve(Views.Num());
    for (const FPureMassView& View : Views)
        if (View.Id != INDEX_NONE && View.Health > 0.f && View.State != 3) Living.Add(View.Id);

    bool bChanged = false;
    for (int32 Index = NetEntities.Items.Num() - 1; Index >= 0; --Index)
    {
        if (!Living.Contains(NetEntities.Items[Index].Id))
        {
            NetEntities.Items.RemoveAtSwap(Index);
            NetEntities.MarkArrayDirty();
            bChanged = true;
        }
    }
    TMap<int32, int32> Indices;
    Indices.Reserve(NetEntities.Items.Num());
    for (int32 Index = 0; Index < NetEntities.Items.Num(); ++Index)
        Indices.Add(NetEntities.Items[Index].Id, Index);

    for (const FPureMassView& View : Views)
    {
        if (!Living.Contains(View.Id)) continue;
        int32* Existing = Indices.Find(View.Id);
        const int32 Index = Existing ? *Existing : NetEntities.Items.AddDefaulted();
        FPureMassNetEntity& Item = NetEntities.Items[Index];
        if (Item.SetFromView(View))
        {
            NetEntities.MarkItemDirty(Item);
            bChanged = true;
        }
        if (!Existing) Indices.Add(View.Id, Index);
    }
    if (bChanged) ForceNetUpdate();
}

void APureMassCrowd::ApplyReplicatedSnapshot()
{
    if (HasAuthority() || !GetWorld()) return;
    TArray<FPureMassView> Views;
    Views.Reserve(NetEntities.Items.Num());
    for (const FPureMassNetEntity& Item : NetEntities.Items)
        if (Item.Id != INDEX_NONE && Item.Type && Item.Health > 0.f && Item.State != 3) Views.Add(Item.ToView());
    if (UPureMassSubsystem* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>()) Mass->SetClientSnapshots(Views);
    if (GetNetMode() != NM_DedicatedServer) ReconcileInstances(Views);
}

int32 APureMassCrowd::FindOrCreateBatch(UPureMassMonsterType* Type)
{
    for (int32 Index = 0; Index < RenderBatches.Num(); ++Index)
        if (RenderBatches[Index].Type == Type) return Index;
    if (!Type || RejectedTypes.Contains(Type)) return INDEX_NONE;

    // Registering original meshes can trigger material usage edits in the editor.
    // Rendering is deliberately restricted to the new cloned asset tree.
    bool bValid = IsPureMassAsset(Type->Mesh) && IsPureMassAsset(Type->AnimationProvider);
    if (bValid)
    {
        bValid = Type->AnimationProvider->GetSkinnedAsset() == Type->Mesh
            && !Type->AnimationProvider->GetLayers().IsEmpty()
            && Type->AnimationProvider->GetSequences().IsValidIndex(Type->IdleAnimation)
            && Type->AnimationProvider->GetSequences().IsValidIndex(Type->RunAnimation)
            && Type->AnimationProvider->GetSequences().IsValidIndex(Type->AttackAnimation);
        for (const FSkeletalMaterial& Material : Type->Mesh->GetMaterials())
            bValid &= IsPureMassAsset(Material.MaterialInterface);
    }
    if (!bValid)
    {
        RejectedTypes.Add(Type);
        UE_LOG(LogPureMassCrowd, Error, TEXT("Cannot render %s: use matching /Game/PureMass/ cloned mesh, materials and animation provider with valid state indices."), *GetNameSafe(Type));
        return INDEX_NONE;
    }

    FPureMassRenderBatch Batch;
    Batch.Type = Type;
    Batch.Component = NewObject<UInstancedSkinnedMeshComponent>(this);
    Batch.Component->SetupAttachment(RootComponent);
    Batch.Component->SetMobility(EComponentMobility::Movable);
    Batch.Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Batch.Component->SetGenerateOverlapEvents(false);
    Batch.Component->SetCanEverAffectNavigation(false);
    Batch.Component->SetSkinnedAssetAndUpdate(Type->Mesh);
    Batch.Component->SetAnimationMinScreenSize(-1.f);
    Batch.Playback = UAnimSequenceTransformProviderDataInstance::CreateAnimSequenceTransformProviderDataInstance(
        Type->AnimationProvider, Batch.Component);
    if (!Batch.Playback)
    {
        Batch.Component->DestroyComponent();
        RejectedTypes.Add(Type);
        return INDEX_NONE;
    }
    Batch.Component->SetTransformProvider(Batch.Playback);
    AddInstanceComponent(Batch.Component);
    Batch.Component->RegisterComponent();
    return RenderBatches.Add(Batch);
}

void APureMassCrowd::SetAnimation(FPureMassRenderInstance& Instance, uint8 State)
{
    if (Instance.State == State) return;
    const FPureMassRenderBatch& Batch = RenderBatches[Instance.BatchIndex];
    FAnimSequenceTrackAutoPlayData Play;
    Play.SequenceIndex = State == 2 ? Batch.Type->AttackAnimation : State == 1 ? Batch.Type->RunAnimation : Batch.Type->IdleAnimation;
    Play.Position = 0.f;
    Play.PlayRate = 1.f;
    Play.BlendTime = Instance.State == 255 ? 0.f : 0.1f;
    Play.LoopMode = State == 2 ? EAnimSequenceTrackLoopMode::Clamp : EAnimSequenceTrackLoopMode::Loop;
    Batch.Playback->SetAutoPlayData(Instance.Track, 0, Play);
    Instance.State = State;
}

void APureMassCrowd::ReconcileInstances(const TArray<FPureMassView>& Views)
{
    TSet<int32> Present;
    Present.Reserve(Views.Num());
    for (const FPureMassView& View : Views)
    {
        if (View.Id == INDEX_NONE || !View.Type || View.Health <= 0.f || View.State == 3) continue;
        const int32 BatchIndex = FindOrCreateBatch(View.Type);
        if (BatchIndex == INDEX_NONE) continue;
        Present.Add(View.Id);
        FPureMassRenderInstance* Existing = RenderInstances.Find(View.Id);
        if (Existing && Existing->BatchIndex != BatchIndex)
        {
            RemoveRenderInstance(*Existing);
            RenderInstances.Remove(View.Id);
            Existing = nullptr;
        }
        if (!Existing)
        {
            FPureMassRenderInstance NewInstance;
            NewInstance.BatchIndex = BatchIndex;
            NewInstance.Track = RenderBatches[BatchIndex].Playback->AllocateTrack();
            if (NewInstance.Track == INDEX_NONE) continue;
            NewInstance.DisplayLocation = View.Location;
            NewInstance.StartLocation = View.Location;
            NewInstance.TargetLocation = View.Location;
            if (!View.Velocity.IsNearlyZero())
                NewInstance.Facing = FRotator(0.f, View.Velocity.Rotation().Yaw, 0.f).Quaternion();
            SetAnimation(NewInstance, View.State);
            const FTransform WorldTransform = View.Type->MeshOffset * FTransform(NewInstance.Facing, View.Location);
            NewInstance.Instance = RenderBatches[BatchIndex].Component->AddInstance(WorldTransform, NewInstance.Track, true);
            if (!NewInstance.Instance.IsValid())
            {
                RenderBatches[BatchIndex].Playback->DeallocateTrack(NewInstance.Track);
                continue;
            }
            Existing = &RenderInstances.Add(View.Id, NewInstance);
        }
        Existing->StartLocation = Existing->DisplayLocation;
        Existing->TargetLocation = View.Location;
        Existing->InterpolationAge = 0.f;
        if (!View.Velocity.IsNearlyZero())
            Existing->Facing = FRotator(0.f, View.Velocity.Rotation().Yaw, 0.f).Quaternion();
        SetAnimation(*Existing, View.State);
    }
    for (auto Iterator = RenderInstances.CreateIterator(); Iterator; ++Iterator)
    {
        if (!Present.Contains(Iterator.Key()))
        {
            RemoveRenderInstance(Iterator.Value());
            Iterator.RemoveCurrent();
        }
    }
}

void APureMassCrowd::UpdateTransforms(float DeltaSeconds)
{
    for (TPair<int32, FPureMassRenderInstance>& Entry : RenderInstances)
    {
        FPureMassRenderInstance& Instance = Entry.Value;
        Instance.InterpolationAge += DeltaSeconds;
        const float Alpha = HasAuthority() ? 1.f : FMath::Clamp(Instance.InterpolationAge / SnapshotInterval, 0.f, 1.f);
        Instance.DisplayLocation = FMath::Lerp(Instance.StartLocation, Instance.TargetLocation, Alpha);
        const FPureMassRenderBatch& Batch = RenderBatches[Instance.BatchIndex];
        const FTransform WorldTransform = Batch.Type->MeshOffset * FTransform(Instance.Facing, Instance.DisplayLocation);
        Batch.Component->SetInstanceTransform(Instance.Instance, WorldTransform, true);
    }
}

void APureMassCrowd::RemoveRenderInstance(FPureMassRenderInstance& Instance)
{
    if (!RenderBatches.IsValidIndex(Instance.BatchIndex)) return;
    const FPureMassRenderBatch& Batch = RenderBatches[Instance.BatchIndex];
    if (Batch.Component) Batch.Component->RemoveInstance(Instance.Instance);
    if (Batch.Playback && Instance.Track != INDEX_NONE) Batch.Playback->DeallocateTrack(Instance.Track);
    Instance.Track = INDEX_NONE;
}

void APureMassCrowd::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    for (TPair<int32, FPureMassRenderInstance>& Entry : RenderInstances) RemoveRenderInstance(Entry.Value);
    RenderInstances.Empty();
    for (FPureMassRenderBatch& Batch : RenderBatches)
        if (Batch.Component) Batch.Component->DestroyComponent();
    RenderBatches.Empty();
    if (!HasAuthority() && GetWorld())
        if (UPureMassSubsystem* Mass = GetWorld()->GetSubsystem<UPureMassSubsystem>()) Mass->SetClientSnapshots({});
    NetEntities.Owner.Reset();
    Super::EndPlay(EndPlayReason);
}

int32 APureMassCrowd::GetRenderedInstanceCount() const
{
    int32 Count = 0;
    for (const FPureMassRenderBatch& Batch : RenderBatches)
        if (Batch.Component) Count += Batch.Component->GetInstanceCount();
    return Count;
}

int32 APureMassCrowd::GetReplicatedEntityCount() const { return NetEntities.Items.Num(); }
int32 APureMassCrowd::GetRenderComponentCount() const { return RenderBatches.Num(); }
int32 APureMassCrowd::GetAnimationTrackCount() const { return RenderInstances.Num(); }

UAnimSequenceTransformProviderData* APureMassCrowd::CreateAnimationProvider(UAnimBank* Bank)
{
#if WITH_EDITOR
    if (!IsPureMassAsset(Bank) || !IsPureMassAsset(Bank->Asset)) return nullptr;
    const FString NewName = Bank->GetName() + TEXT("_ASTP");
    const FString NewPackage = FPackageName::GetLongPackagePath(Bank->GetOutermost()->GetName()) / NewName;
    // The engine helper does not reliably check an existing on-disk asset. Never overwrite one.
    if (FPackageName::DoesPackageExist(NewPackage) || FindObject<UPackage>(nullptr, *NewPackage)) return nullptr;
    UAnimSequenceTransformProviderData* Provider = UAnimSequenceTransformProviderData::CreateFromAnimBank(Bank);
    if (Provider) Provider->PostEditChange();
    return Provider;
#else
    return nullptr;
#endif
}
