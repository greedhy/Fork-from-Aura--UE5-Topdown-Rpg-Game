#include "StoneGolem/StoneGolemCharacter.h"
#include "StoneGolem/StoneGolemAbility.h"
#include "AbilitySystem/MyAbilitySystemLibrary.h"
#include "AbilitySystem/Data/CharacterClassInfo.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Components/CapsuleComponent.h"
#include "ProceduralMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraComponent.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"

AStoneGolemCharacter::AStoneGolemCharacter()
{
    PrimaryActorTick.bCanEverTick=true;
    Tags.AddUnique(TEXT("Enemy"));
    Hammer=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StoneHammer"));
    Shield=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StoneShield"));
    Hammer->SetupAttachment(GetMesh(),TEXT("weapon_rSocket"));
    Shield->SetupAttachment(GetMesh(),TEXT("weapon_lSocket"));
    Hammer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Shield->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Footprint=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("AttackFootprint"));
    Footprint->SetupAttachment(GetRootComponent());
    Footprint->SetAbsolute(true,true,true);
    Footprint->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Footprint->CastShadow=false;
    Exclamation=CreateDefaultSubobject<UTextRenderComponent>(TEXT("AttackExclamation"));
    Exclamation->SetupAttachment(GetRootComponent());
    Exclamation->SetText(FText::FromString(TEXT("!")));
    Exclamation->SetTextRenderColor(FColor::Red);
    Exclamation->SetWorldSize(60);
    Exclamation->SetHorizontalAlignment(EHTA_Center);
    Exclamation->SetVisibility(false);
    GetMesh()->SetRelativeLocation(FVector(0,0,-89));
    GetMesh()->SetRelativeRotation(FRotator(0,-90,0));
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetCapsuleComponent()->InitCapsuleSize(45,89);
}
void AStoneGolemCharacter::ApplyConfig()
{
    if(!MonsterConfig) return;
    if(MonsterConfig->Mesh && GetMesh()->GetSkeletalMeshAsset()!=MonsterConfig->Mesh) GetMesh()->SetSkeletalMeshAsset(MonsterConfig->Mesh);
    if(MonsterConfig->AnimClass && GetMesh()->GetAnimClass()!=MonsterConfig->AnimClass) GetMesh()->SetAnimInstanceClass(MonsterConfig->AnimClass);
    Hammer->SetStaticMesh(MonsterConfig->Hammer); Shield->SetStaticMesh(MonsterConfig->Shield);
    BehaviorTree=MonsterConfig->Behavior;
    BaseWalkSpeed=MonsterConfig->WalkSpeed;
    GetCharacterMovement()->MaxWalkSpeed=BaseWalkSpeed;
}
void AStoneGolemCharacter::OnConstruction(const FTransform& Transform){Super::OnConstruction(Transform);ApplyConfig();}
void AStoneGolemCharacter::BeginPlay(){ApplyConfig();Super::BeginPlay();}
void AStoneGolemCharacter::GrantEnemyAbilities()
{
    // A previous life may have died while its stationary attack disabled controller rotation.
    GetCharacterMovement()->bUseControllerDesiredRotation=GetClass()->GetDefaultObject<AStoneGolemCharacter>()->GetCharacterMovement()->bUseControllerDesiredRotation;
    if(!HasAuthority() || !MonsterConfig) return;
    auto Give=[this](TSubclassOf<UGameplayAbility> Class)
    {
        if(Class && !AbilitySystemComponent->FindAbilitySpecFromClass(Class)) AbilitySystemComponent->GiveAbility(FGameplayAbilitySpec(Class,Level));
    };
    // This elite deliberately has no generic hit-react montage: ordinary hits do not interrupt attacks.
    Give(UStoneGolemSelectAttack::StaticClass());
    for(const auto Class:MonsterConfig->Attacks) Give(Class);
    bAttackActive=false;
}
bool AStoneGolemCharacter::TryAttackIndex(int32 Index)
{
    if(!HasAuthority() || !MonsterConfig || !MonsterConfig->Attacks.IsValidIndex(Index)) return false;
    const auto Class=MonsterConfig->Attacks[Index];
    return Class && AbilitySystemComponent->TryActivateAbilityByClass(Class);
}
bool AStoneGolemCharacter::TryChooseAttack()
{
    if(!HasAuthority() || bDead || bAttackActive || !MonsterConfig) return false;
    TArray<TPair<int32,float>> Choices;float Total=0;
    for(int32 Index=0;Index<MonsterConfig->Attacks.Num();++Index)
    {
        auto* Spec=AbilitySystemComponent->FindAbilitySpecFromClass(MonsterConfig->Attacks[Index]);
        const auto* Ability=Spec?Cast<UStoneGolemAttackAbility>(Spec->Ability):nullptr;
        if(Ability && Ability->AttackConfig && Ability->CanActivateAbility(Spec->Handle,AbilitySystemComponent->AbilityActorInfo.Get()))
        {
            Total+=Ability->AttackConfig->Tuning.SelectionWeight;
            Choices.Emplace(Index,Total);
        }
    }
    if(Choices.IsEmpty()) return false;
    const float Roll=FMath::FRand()*Total;
    for(const auto& Choice:Choices) if(Roll<=Choice.Value) return TryAttackIndex(Choice.Key);
    return TryAttackIndex(Choices.Last().Key);
}
int32 AStoneGolemCharacter::BeginAttack(const FStoneGolemAttackTuning& Tuning,const FVector& Center,float Yaw)
{
    if(!HasAuthority() || bDead || bAttackActive) return 0;
    ClearImpact(); bAttackActive=true;
    Presentation.Serial=++Generation;Presentation.Lease=GetDungeonPoolLease();Presentation.Phase=1;
    Presentation.Tuning=Tuning;Presentation.Center=Center;Presentation.Yaw=Yaw;
    OnRep_Presentation();ForceNetUpdate();return Generation;
}
bool AStoneGolemCharacter::IsAttackCurrent(int32 Serial,int32 Lease) const
{
    return Serial!=0 && bAttackActive && !bDead && !IsDungeonPoolSleeping() && Generation==Serial && GetDungeonPoolLease()==Lease;
}
void AStoneGolemCharacter::UpdateWarning(int32 Serial,const FVector& Center,float Yaw)
{
    if(Serial!=Generation || !bAttackActive || Presentation.Phase!=1) return;
    Presentation.Center=Center;Presentation.Yaw=Yaw;OnRep_Presentation();ForceNetUpdate();
}
void AStoneGolemCharacter::ShowImpact(int32 Serial,const FVector& Impact)
{
    if(Serial!=Generation || !bAttackActive) return;
    Presentation.Phase=2;Presentation.Impact=Impact;OnRep_Presentation();ForceNetUpdate();
}
void AStoneGolemCharacter::FinishAttack(int32 Serial)
{
    if(Serial!=Generation) return;
    bAttackActive=false;Presentation.Phase=0;OnRep_Presentation();ForceNetUpdate();
}
void AStoneGolemCharacter::InvalidateEnemyAttack()
{
    // Clients must not overwrite a newer presentation that arrived before its life RepNotify.
    if(HasAuthority()) {++Generation;bAttackActive=false;Presentation.Serial=Generation;Presentation.Phase=0;ForceNetUpdate();}
    Footprint->ClearAllMeshSections();Exclamation->SetVisibility(false);ClearImpact();
}
void AStoneGolemCharacter::StunTagChanged(FGameplayTag Tag,int32 Count)
{
    Super::StunTagChanged(Tag,Count);
    if(HasAuthority() && Count>0) InvalidateEnemyAttack();
}
void AStoneGolemCharacter::ClearImpact()
{
    GetWorldTimerManager().ClearTimer(ImpactExpiry);
    if(ImpactComponent){ImpactComponent->DestroyComponent();ImpactComponent=nullptr;}
}
void AStoneGolemCharacter::OnRep_Presentation()
{
    if(GetNetMode()==NM_DedicatedServer) return;
    const bool Valid=!bDead && !IsDungeonPoolSleeping() && GetDungeonPoolLease()==Presentation.Lease;
    const bool Warning=Valid && Presentation.Phase==1;
    Exclamation->SetVisibility(Warning && Presentation.Tuning.bExclamation);
    Exclamation->SetRelativeLocation(Presentation.Tuning.HeadOffset);
    if(Warning) BuildFootprint();else Footprint->ClearAllMeshSections();
    if(!Valid || Presentation.Phase==0) ClearImpact();
    if(Valid && Presentation.Phase==2 && LastImpact!=Presentation.Serial)
    {
        LastImpact=Presentation.Serial;ClearImpact();
        if(Presentation.Tuning.ImpactEffect)
        {
            ImpactComponent=UNiagaraFunctionLibrary::SpawnSystemAtLocation(this,Presentation.Tuning.ImpactEffect,
                Presentation.Impact,FRotator::ZeroRotator,FVector(Presentation.Tuning.ImpactScale),false,true);
            GetWorldTimerManager().SetTimer(ImpactExpiry,this,&ThisClass::ClearImpact,Presentation.Tuning.ImpactLifetime,false);
        }
    }
}
void AStoneGolemCharacter::BuildFootprint()
{
    const auto& T=Presentation.Tuning;
    TArray<FVector> Vertices;TArray<int32> Triangles;TArray<FVector> Normals;TArray<FVector2D> UV;
    TArray<FLinearColor> Colors;TArray<FProcMeshTangent> Tangents;
    StoneGolemGeometry::BuildSurface(GetWorld(),this,T,Presentation.Center,Presentation.Yaw,Vertices,Triangles);
    for(auto& Vertex:Vertices)
    {
        Vertex.Z+=2;Normals.Add(FVector::UpVector);UV.Add(FVector2D::ZeroVector);
        Colors.Add(FLinearColor::Red);Tangents.Add(FProcMeshTangent(1,0,0));
    }
    Footprint->SetWorldTransform(FTransform::Identity);
    Footprint->CreateMeshSection_LinearColor(0,Vertices,Triangles,Normals,UV,Colors,Tangents,false);
    Footprint->SetMaterial(0,T.WarningMaterial);
}
void AStoneGolemCharacter::Tick(float Delta)
{
    Super::Tick(Delta);
    if(Exclamation->IsVisible()) if(const auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0))
        Exclamation->SetWorldRotation((Camera->GetCameraLocation()-Exclamation->GetComponentLocation()).Rotation());
}
void AStoneGolemCharacter::EndPlay(EEndPlayReason::Type Reason){ClearImpact();Super::EndPlay(Reason);}
void AStoneGolemCharacter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AStoneGolemCharacter,Presentation);
}
