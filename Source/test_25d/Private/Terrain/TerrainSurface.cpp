#include "Terrain/TerrainSurface.h"
#include "Terrain/TerrainStatusComponent.h"
#include "Character/BaseCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NiagaraComponent.h"
#include "TimerManager.h"
#include "AbilitySystem/MyAbilitySystemLibrary.h"
#include "Net/UnrealNetwork.h"

ATerrainSurface::ATerrainSurface()
{
    bReplicates = true;
    PrimaryActorTick.bCanEverTick = false;
    Area = CreateDefaultSubobject<UBoxComponent>(TEXT("SurfaceArea"));
    SetRootComponent(Area);
    Area->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Ground = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Ground"));
    Ground->SetupAttachment(Area);
    Ground->SetCollisionProfileName(TEXT("BlockAll"));
    SurfaceParticles = CreateDefaultSubobject<UNiagaraComponent>(TEXT("SurfaceParticles"));
    SurfaceParticles->SetupAttachment(Area);
    SurfaceParticles->SetAutoActivate(false);
}

void ATerrainSurface::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Area->SetBoxExtent(FVector(FMath::Max(50.f, SurfaceSize.X)*.5f, FMath::Max(50.f, SurfaceSize.Y)*.5f, FMath::Max(2.f, ContactHeight)));
    if (!Config) return;
    Ground->SetStaticMesh(Config->GroundMesh);
    if (Config->GroundMesh)
    {
        const FBox Bounds = Config->GroundMesh->GetBoundingBox();
        const FVector Size = Bounds.GetSize();
        const FVector Scale(SurfaceSize.X/FMath::Max(1.f, Size.X), SurfaceSize.Y/FMath::Max(1.f, Size.Y), 1.f);
        Ground->SetRelativeScale3D(Scale);
        Ground->SetRelativeLocation(FVector(-Bounds.GetCenter().X*Scale.X, -Bounds.GetCenter().Y*Scale.Y, -Bounds.Max.Z));
    }
    SurfaceParticles->SetAsset(Config->SurfaceVFX);
    SurfaceParticles->SetRelativeLocation(FVector(0,0,5));
    SurfaceParticles->SetRelativeScale3D(FVector(SurfaceSize.X/400.f, SurfaceSize.Y/400.f, 1.f));
}

void ATerrainSurface::BeginPlay()
{
    Super::BeginPlay();
    if (bOnlyAffectCasterEnemies) Ground->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (GetNetMode() != NM_DedicatedServer && Config && Config->SurfaceVFX && bEnabled)
        SurfaceParticles->Activate(true);
    if (HasAuthority())
    {
        GetWorldTimerManager().SetTimer(ScanTimer, this, &ATerrainSurface::UpdateContacts, .2f, true);
        UpdateContacts();
    }
}

bool ATerrainSurface::CanAffectCharacter(ABaseCharacter* Character) const
{
    if (!bEnabled || !Config || !IsValid(Character) || Character->IsDead_Implementation() || !Character->GetAbilitySystemComponent()) return false;
    if (bOnlyAffectCasterEnemies && (!IsValid(GetOwner()) || Character == GetOwner() || !UMyAbilitySystemLibrary::IsNotFriend(GetOwner(), Character))) return false;
    if (Character->ActorHasTag(TEXT("Player")) && !bAffectPlayers) return false;
    if (Character->ActorHasTag(TEXT("Enemy")) && !bAffectEnemies) return false;
    if (bRequireGrounded && !Character->GetCharacterMovement()->IsMovingOnGround()) return false;
    const FVector Feet = Character->GetActorLocation() - FVector(0,0,Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    const FVector Local = GetActorTransform().InverseTransformPosition(Feet);
    return FMath::Abs(Local.X) <= SurfaceSize.X*.5f && FMath::Abs(Local.Y) <= SurfaceSize.Y*.5f
        && FMath::Abs(Local.Z) <= ContactHeight;
}

void ATerrainSurface::UpdateContacts()
{
    if (!HasAuthority() || !bEnabled || !Config) return;
    TArray<FOverlapResult> Hits;
    const FVector Scale = GetActorScale3D().GetAbs();
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_Pawn);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    GetWorld()->OverlapMultiByObjectType(Hits, GetActorLocation()+FVector(0,0,100), GetActorQuat(), Objects,
        FCollisionShape::MakeBox(FVector(SurfaceSize.X*.5f*Scale.X+100, SurfaceSize.Y*.5f*Scale.Y+100, 250)),
        FCollisionQueryParams(SCENE_QUERY_STAT(TerrainContacts), false, this));
    TSet<ABaseCharacter*> Seen;
    for (const FOverlapResult& Hit : Hits)
    {
        ABaseCharacter* Character = Cast<ABaseCharacter>(Hit.GetActor());
        if (Character && !Seen.Contains(Character) && CanAffectCharacter(Character))
        {
            Seen.Add(Character);
            if (auto* Status = Character->FindComponentByClass<UTerrainStatusComponent>()) Status->RefreshContact(this);
        }
    }
}

void ATerrainSurface::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(ScanTimer);
    Super::EndPlay(Reason);
}

void ATerrainSurface::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ATerrainSurface, bOnlyAffectCasterEnemies);
    DOREPLIFETIME(ATerrainSurface, SurfaceSize);
}

void ATerrainSurface::OnRep_SurfaceSize() { OnConstruction(GetActorTransform()); }
