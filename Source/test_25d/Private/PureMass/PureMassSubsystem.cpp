#include "PureMass/PureMassSubsystem.h"
#include "PureMass/PureMassIncomingDamageEffect.h"
#include "PureMass/PureMassPlayerController.h"
#include "PureMass/PureMassLegacyProjectile.h"
#include "Actor/MyProjectile.h"
#include "test_25d/test_25d.h"
#include "MassEntitySubsystem.h"
#include "MassEntityManager.h"
#include "MassCommandBuffer.h"
#include "AbilitySystemComponent.h"
#include "AbilitySystemBlueprintLibrary.h"
#include "AbilitySystem/MyAttributeSet.h"
#include "AbilitySystem/MyAbilitySystemLibrary.h"
#include "AbilitySystem/Data/CharacterClassInfo.h"
#include "Interface/CombatInterface.h"
#include "MyGameplayTags.h"
#include "GameplayEffect.h"
#include "Engine/CurveTable.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Character.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "NavigationPath.h"
#include "Terrain/TerrainSurface.h"

namespace
{
float FinitePositive(float Value, float Fallback = 0.f)
{
    return FMath::IsFinite(Value) ? FMath::Max(0.f, Value) : Fallback;
}
float Attribute(const UAbilitySystemComponent* ASC, FGameplayAttribute Attr)
{
    return ASC ? FinitePositive(ASC->GetNumericAttribute(Attr)) : 0.f;
}
float BalanceCurve(const UObject* Context, FName Name, int32 Level, float Fallback)
{
    const UCharacterClassInfo* Info = UMyAbilitySystemLibrary::GetCharacterClassInfo(Context);
    if (Info && Info->DamageCalConst)
        if (const FRealCurve* Curve = Info->DamageCalConst->FindCurve(Name, TEXT("PureMass"), false))
            return FinitePositive(Curve->Eval(Level), Fallback);
    return Fallback;
}
bool Alive(const APawn* Pawn)
{
    return IsValid(Pawn) && (!Pawn->Implements<UCombatInterface>() || !ICombatInterface::Execute_IsDead(Pawn));
}
}

bool UPureMassSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
    return Type == EWorldType::Game || Type == EWorldType::PIE;
}
void UPureMassSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    Mass = Collection.InitializeDependency<UMassEntitySubsystem>();
}
bool UPureMassSubsystem::IsAuthority() const
{
    return GetWorld() && GetWorld()->GetNetMode() != NM_Client;
}
void UPureMassSubsystem::Enable()
{
    check(IsInGameThread());
    if (bEnabled || !Mass) return;
    Grid.Reset(256);
    if (IsAuthority())
    {
        const UScriptStruct* Fragments[] = { FPureMassFragment::StaticStruct() };
        Archetype = Mass->GetMutableEntityManager().CreateArchetype(Fragments);
    }
    bEnabled = true;
    LegacyFireBoltClass = LoadClass<AMyProjectile>(nullptr,
        TEXT("/Game/BluePrints/AbilitySystem/Player/Ability/Fire/FireBolt/BP_FireBolt.BP_FireBolt_C"));
    ProjectileSpawnHandle = GetWorld()->AddOnActorSpawnedHandler(
        FOnActorSpawned::FDelegate::CreateUObject(this, &ThisClass::AdaptLegacyProjectile));
}
void UPureMassSubsystem::AdaptLegacyProjectile(AActor* Actor)
{
    // Explicit allow-list: orbiting and other specialised projectiles have their own lifecycle.
    if (!bEnabled || !LegacyFireBoltClass || Actor->GetClass() != LegacyFireBoltClass
        || Actor->FindComponentByClass<UPureMassLegacyProjectile>()) return;
    auto* Adapter = NewObject<UPureMassLegacyProjectile>(Actor);
    Actor->AddInstanceComponent(Adapter);
    Adapter->RegisterComponent();
}
int32 UPureMassSubsystem::SpawnMonster(UPureMassMonsterType* Type, FVector Location, FName Room)
{
    check(IsInGameThread());
    if (!bEnabled || !IsAuthority() || !Mass || !IsValid(Type) || Location.ContainsNaN()
        || !FMath::IsFinite(Type->Radius) || !FMath::IsFinite(Type->HalfHeight)
        || Type->Radius <= 0 || Type->HalfHeight < Type->Radius
        || !FMath::IsFinite(Type->Health) || Type->Health <= 0 || NextId > MAX_int32) return INDEX_NONE;
    FMassEntityManager& Manager = Mass->GetMutableEntityManager();
    if (Manager.IsProcessing()) return INDEX_NONE;
    // Authoring locations are capsule centres. Snap the corresponding feet to navmesh when available.
    if (UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
    {
        FNavLocation Projected;
        if (Nav->ProjectPointToNavigation(Location - FVector(0,0,Type->HalfHeight), Projected,
            FVector(Type->Radius*2, Type->Radius*2, FMath::Max(200.f, Type->HalfHeight*2))))
            Location = Projected.Location + FVector(0,0,Type->HalfHeight + 1.f);
    }
    const FMassEntityHandle Handle = Manager.CreateEntity(Archetype);
    FPureMassFragment& Fragment = Manager.GetFragmentDataChecked<FPureMassFragment>(Handle);
    Fragment.Id = int32(NextId++);
    Fragment.Type = Type;
    Fragment.Location = Location;
    Fragment.Room = Room;
    Fragment.Health = Fragment.MaxHealth = Type->Health;
    Entities.Add(Fragment.Id, Handle);
    RetainedTypes.AddUnique(Type);
    LargestRadius = FMath::Max(LargestRadius, Type->Radius);
    LargestHalfHeight = FMath::Max(LargestHalfHeight, Type->HalfHeight);
    Publish(Fragment);
    return Fragment.Id;
}
void UPureMassSubsystem::Publish(const FPureMassFragment& Fragment)
{
    if (Fragment.Health <= 0) return;
    FPureMassView& View = Views.FindOrAdd(Fragment.Id);
    View.Id = Fragment.Id; View.Location = Fragment.Location; View.Velocity = Fragment.Velocity;
    View.Health = Fragment.Health; View.MaxHealth = Fragment.MaxHealth;
    View.State = Fragment.State; View.Type = Fragment.Type.Get();
    Grid.Update(Fragment.Id, Fragment.Location, Fragment.Room);
}
bool UPureMassSubsystem::Resolve(int32 Id, FPureMassView& OutView) const
{
    OutView = FPureMassView();
    if (!bEnabled || Id <= 0) return false;
    if (const FPureMassView* View = Views.Find(Id); View && View->Health > 0)
    { OutView = *View; return true; }
    return false;
}
TArray<int32> UPureMassSubsystem::QueryRadius(FVector Center, float Radius) const
{
    TArray<int32> Result;
    if (!bEnabled || Center.ContainsNaN() || !FMath::IsFinite(Radius) || Radius < 0) return Result;
    for (uint64 Id : Grid.Query(Center, Radius))
        if (const FPureMassView* View = Views.Find(int32(Id)); View && View->Health > 0) Result.Add(int32(Id));
    Result.Sort();
    return Result;
}
int32 UPureMassSubsystem::Sweep(FVector Start, FVector End, float Radius, float& OutTime, const TSet<int32>* Ignored) const
{
    OutTime = 1.f;
    if (!bEnabled || Start.ContainsNaN() || End.ContainsNaN() || !FMath::IsFinite(Radius) || Radius < 0) return INDEX_NONE;
    int32 Result = INDEX_NONE;
    const FVector Center = (Start + End)*.5;
    const double BroadRadius = FVector::Distance(Start, End)*.5 + Radius + LargestHalfHeight;
    for (const uint64 RawId : Grid.Query(Center, BroadRadius))
    {
        const int32 Id = int32(RawId);
        if (Ignored && Ignored->Contains(Id)) continue;
        const FPureMassView* View = Views.Find(Id);
        if (!View || View->Health <= 0 || !View->Type) continue;
        float Time = 1;
        if (PureMassGeometry::SweepCapsule(Start, End, Radius, View->Location,
            View->Type->Radius, View->Type->HalfHeight, Time)
            && (Time < OutTime || (Time == OutTime && (Result == INDEX_NONE || Id < Result))))
        { OutTime = Time; Result = Id; }
    }
    return Result;
}
TArray<FPureMassView> UPureMassSubsystem::GetSnapshots() const
{
    TArray<FPureMassView> Result;
    if (bEnabled) Views.GenerateValueArray(Result);
    Result.Sort([](const FPureMassView& A, const FPureMassView& B) { return A.Id < B.Id; });
    return Result;
}
void UPureMassSubsystem::SetClientSnapshots(const TArray<FPureMassView>& Snapshots)
{
    check(IsInGameThread());
    if (IsAuthority()) return;
    Enable();
    Views.Reset(); Grid.Reset(256); RetainedTypes.Reset();
    LargestRadius = 32; LargestHalfHeight = 60;
    for (const FPureMassView& View : Snapshots)
        if (View.Id > 0 && View.Health > 0 && FMath::IsFinite(View.Health) && !View.Location.ContainsNaN() && IsValid(View.Type))
        {
            Views.Add(View.Id, View);
            Grid.Update(View.Id, View.Location, NAME_None);
            RetainedTypes.AddUnique(View.Type);
            LargestRadius = FMath::Max(LargestRadius, View.Type->Radius);
            LargestHalfHeight = FMath::Max(LargestHalfHeight, View.Type->HalfHeight);
        }
}
FMassEntityHandle UPureMassSubsystem::GetEntity(int32 Id) const
{
    const FMassEntityHandle* Handle = Entities.Find(Id);
    return Handle ? *Handle : FMassEntityHandle();
}
float UPureMassSubsystem::EvaluateDamage(const FPureMassFragment& Fragment, const FPureMassDamage& Damage, bool& bBlocked, bool& bCritical) const
{
    bBlocked = bCritical = false;
    const UPureMassMonsterType* Type = Fragment.Type.Get();
    if (!Type) return 0;
    UAbilitySystemComponent* ASC = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Damage.Source.Get());
    const int32 SourceLevel = Damage.Source.IsValid() && Damage.Source->Implements<UCombatInterface>()
        ? ICombatInterface::Execute_GetPlayerLevel(Damage.Source.Get()) : 1;
    float Value = FinitePositive(Damage.Amount);
    // Mirrors existing damage order: resistance, block, crit, effective armour. Pure bypasses resistance only.
    if (Damage.DamageType != FMyGameplayTags::Get().Damage_Pure)
        if (const float* Resistance = Type->Resistances.Find(Damage.DamageType))
            Value *= 1.f - FMath::Clamp(FinitePositive(*Resistance), 0.f, 100.f)*.01f;
    bBlocked = FMath::FRand()*100.f < FMath::Clamp(FinitePositive(Type->BlockChance), 0.f, 100.f);
    if (bBlocked) Value *= .5f;
    const float ArmorCoefficient = BalanceCurve(this, TEXT("EffectiveArmor"), Type->Level, 1.f);
    // Legacy ExecCalc currently uses EffectiveArmor for critical resistance too; preserve its balance.
    const float CriticalChance = Attribute(ASC, UMyAttributeSet::GetCriticalHitChanceAttribute())
        - FinitePositive(Type->CriticalResistance)*ArmorCoefficient;
    bCritical = FMath::FRand()*100.f < FMath::Clamp(CriticalChance, 0.f, 100.f);
    if (bCritical)
        Value *= 1.f + Attribute(ASC, UMyAttributeSet::GetCriticalHitDamageAttribute())*.01f;
    const float Penetration = FMath::Clamp(Attribute(ASC, UMyAttributeSet::GetArmorPeneAttribute()), 0.f, 100.f);
    // Read the legacy source curve as part of the balance contract; legacy code does not apply this coefficient.
    (void)BalanceCurve(this, TEXT("ArmorPene"), SourceLevel, 1.f);
    const float EffectiveArmor = FinitePositive(Type->Armor)*(1.f - Penetration*.01f);
    return FinitePositive(Value * FMath::Clamp(1.f - EffectiveArmor*ArmorCoefficient*.01f, 0.f, 1.f));
}
float UPureMassSubsystem::DamageFragment(FPureMassFragment& Fragment, float Amount, AActor* Source, bool bBlocked, bool bCritical)
{
    if (Fragment.Health <= 0) return 0;
    const float Removed = FMath::Min(Fragment.Health, FinitePositive(Amount));
    if (Removed <= 0) return 0;
    Fragment.Health -= Removed;
    if (IsValid(Source))
    {
        const auto* Pawn = Cast<APawn>(Source);
        auto* PC = Cast<APureMassPlayerController>(Pawn ? Pawn->GetController() : Source->GetInstigatorController());
        if (PC && PC->GetWorld() == GetWorld())
            PC->QueueMassDamageNumber(Fragment.Id, Fragment.Location, Removed, bBlocked, bCritical);
    }
    if (Fragment.Health > 0) { Publish(Fragment); return Removed; }
    Fragment.State = 3; Fragment.Velocity = FVector::ZeroVector;
    const int32 Id = Fragment.Id;
    const int32 XP = Fragment.Type.IsValid() ? FMath::Max(0, Fragment.Type->XPReward) : 0;
    Views.Remove(Id); Grid.Remove(Id); Dead.AddUnique(Id); ++DeathCount;
    // Publish death before sending any external event: reentrant damage cannot award twice.
    if (IsValid(Source) && XP > 0 && UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Source))
    {
        FGameplayEventData Payload;
        Payload.EventTag = FMyGameplayTags::Get().Attributes_Meta_IncomingXP;
        Payload.EventMagnitude = XP;
        UAbilitySystemBlueprintLibrary::SendGameplayEventToActor(Source, Payload.EventTag, Payload);
    }
    return Removed;
}
float UPureMassSubsystem::ApplyDamage(int32 Id, const FPureMassDamage& Damage)
{
    check(IsInGameThread());
    if (!bEnabled || !IsAuthority() || !Mass || Id <= 0 || !Views.Contains(Id)
        || !FMath::IsFinite(Damage.Amount) || Damage.Amount < 0) return 0;
    const FMassEntityHandle Handle = GetEntity(Id);
    FMassEntityManager& Manager = Mass->GetMutableEntityManager();
    if (!Manager.IsEntityValid(Handle)) return 0;
    FPureMassFragment& Fragment = Manager.GetFragmentDataChecked<FPureMassFragment>(Handle);
    if (Damage.StatusDuration > 0 && FMath::IsFinite(Damage.StatusDuration))
    {
        Fragment.StatusRemaining = FMath::Max(Fragment.StatusRemaining, Damage.StatusDuration);
        Fragment.StatusDPS = FMath::Max(Fragment.StatusDPS, FinitePositive(Damage.DamagePerSecond));
        Fragment.StatusSlow = FMath::Min(Fragment.StatusSlow, FMath::Clamp(FinitePositive(Damage.MovementMultiplier, 1.f), 0.f, 1.f));
        Fragment.StatusSource = Damage.Source;
        if (Damage.bRoot) Fragment.RootRemaining = FMath::Max(Fragment.RootRemaining, Damage.StatusDuration);
    }
    bool bBlocked = false, bCritical = false;
    const float Evaluated = EvaluateDamage(Fragment, Damage, bBlocked, bCritical);
    return DamageFragment(Fragment, Evaluated, Damage.Source.Get(), bBlocked, bCritical);
}

bool UPureMassSubsystem::BeginUpdate(float DeltaSeconds)
{
    check(IsInGameThread());
    if (!bEnabled || !IsAuthority() || !Mass || !FMath::IsFinite(DeltaSeconds) || DeltaSeconds <= 0) return false;
    DeltaTime = FMath::Min(DeltaSeconds, .25f);
    PathsRemaining = 8; // Absolute frame budget, independent of population size.
    Players.Reset();
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
        if (const APlayerController* PC = It->Get(); PC && Alive(PC->GetPawn())) Players.Add(PC->GetPawn());
    bRefreshTerrain = GetWorld()->GetTimeSeconds() >= NextTerrainScan;
    if (bRefreshTerrain)
    {
        NextTerrainScan = GetWorld()->GetTimeSeconds() + .2f;
        Terrain.Reset();
        for (TActorIterator<ATerrainSurface> It(GetWorld()); It; ++It)
            if (It->bEnabled && It->bAffectEnemies && It->Config) Terrain.Add(*It);
    }
    return true;
}

float UPureMassSubsystem::UpdateTerrain(FPureMassFragment& Fragment)
{
    const UPureMassMonsterType* Type = Fragment.Type.Get();
    if (!Type) return 1.f;
    for (auto& Contact : Fragment.TerrainContacts) Contact.Remaining -= DeltaTime;
    if (bRefreshTerrain)
        for (const TWeakObjectPtr<ATerrainSurface>& Weak : Terrain)
        {
            ATerrainSurface* Surface = Weak.Get();
            if (!Surface || !Surface->bEnabled || !Surface->Config || !Surface->bAffectEnemies) continue;
            if (Surface->bOnlyAffectCasterEnemies && (!Surface->GetOwner() || !Surface->GetOwner()->ActorHasTag(TEXT("Player")))) continue;
            const FVector Feet = Fragment.Location - FVector(0,0,Type->HalfHeight);
            const FVector Local = Surface->GetActorTransform().InverseTransformPosition(Feet);
            const FVector Scale = Surface->GetActorScale3D().GetAbs();
            if (Scale.GetMin() < UE_SMALL_NUMBER) continue;
            if (FMath::Abs(Local.X) > Surface->SurfaceSize.X*.5 + Type->Radius/Scale.X
                || FMath::Abs(Local.Y) > Surface->SurfaceSize.Y*.5 + Type->Radius/Scale.Y
                || FMath::Abs(Local.Z)*Scale.Z > Surface->ContactHeight + 12.f) continue;
            if (Surface->bRequireGrounded)
            {
                FHitResult Ground;
                FCollisionQueryParams GroundParams(SCENE_QUERY_STAT(PureMassTerrainGround), false);
                if (!GetWorld()->LineTraceSingleByChannel(Ground, Feet + FVector(0,0,8), Feet - FVector(0,0,16),
                    ECC_WorldStatic, GroundParams) || Ground.Normal.Z < .65f) continue;
            }
            auto* Contact = Fragment.TerrainContacts.FindByPredicate([Surface](const FPureMassFragment::FTerrainContact& C) { return C.Surface == Surface; });
            if (!Contact) Contact = &Fragment.TerrainContacts.AddDefaulted_GetRef();
            Contact->Surface = Surface;
            Contact->Remaining = .3f + (Surface->Config->SurfaceType == ETerrainSurfaceType::Vines ? 0.f : FinitePositive(Surface->Config->ExitDuration));
        }
    Fragment.TerrainContacts.RemoveAll([](const FPureMassFragment::FTerrainContact& Contact)
    { return Contact.Remaining <= 0 || !Contact.Surface.IsValid() || !Contact.Surface->bEnabled || !Contact.Surface->Config; });
    ATerrainSurface* Best[4] = {};
    for (const auto& Contact : Fragment.TerrainContacts)
    {
        ATerrainSurface* Surface = Contact.Surface.Get();
        const uint8 Index = uint8(Surface->Config->SurfaceType);
        if (Index >= 4) continue;
        if (!Best[Index] || (Index == 1 ? Surface->Config->MovementMultiplier < Best[Index]->Config->MovementMultiplier
            : Surface->Config->DamagePerSecond > Best[Index]->Config->DamagePerSecond)) Best[Index] = Surface;
    }
    if (Best[3] && Fragment.RootRecovery <= 0)
    {
        Fragment.RootRemaining = FMath::Max(.1f, FinitePositive(Best[3]->Config->EntangleDuration));
        Fragment.RootRecovery = Fragment.RootRemaining + FMath::Max(.5f, FinitePositive(Best[3]->Config->EntangleRecovery));
    }
    for (int32 Index : {0, 2})
        if (Best[Index])
        {
            ATerrainSurface* Surface = Best[Index];
            DamageFragment(Fragment, FinitePositive(Surface->Config->DamagePerSecond)*DeltaTime,
                Surface->bOnlyAffectCasterEnemies ? Surface->GetOwner() : nullptr);
            if (Fragment.Health <= 0) return 1.f;
        }
    return Best[1] ? FMath::Clamp(FinitePositive(Best[1]->Config->MovementMultiplier, 1.f), .05f, 1.f) : 1.f;
}

void UPureMassSubsystem::AttackPlayer(FPureMassFragment& Fragment, APawn* Player)
{
    UAbilitySystemComponent* ASC = UAbilitySystemBlueprintLibrary::GetAbilitySystemComponent(Player);
    UPureMassMonsterType* Type = Fragment.Type.Get();
    // Existing incoming-damage handler requires a Character target.
    if (!ASC || !Type || !Cast<ACharacter>(Player)) return;
    float Damage = FinitePositive(Type->AttackDamage);
    Damage *= 1.f - FMath::Clamp(Attribute(ASC, UMyAttributeSet::GetPhysicsResistanceAttribute()), 0.f, 100.f)*.01f;
    const bool bBlock = FMath::FRand()*100.f < FMath::Clamp(Attribute(ASC, UMyAttributeSet::GetBlockChanceAttribute()), 0.f, 100.f);
    if (bBlock) Damage *= .5f;
    const int32 Level = Player->Implements<UCombatInterface>() ? ICombatInterface::Execute_GetPlayerLevel(Player) : 1;
    Damage *= FMath::Clamp(1.f - Attribute(ASC, UMyAttributeSet::GetArmorAttribute()) * BalanceCurve(this, TEXT("EffectiveArmor"), Level, 1.f)*.01f, 0.f, 1.f);
    if (Damage <= 0) return;
    // An instant player-side GE preserves damage/death/replication callbacks. No enemy ASC or adapter Actor.
    FGameplayEffectContextHandle Context = ASC->MakeEffectContext();
    Context.AddInstigator(nullptr, nullptr);
    Context.AddSourceObject(nullptr);
    FHitResult Hit;
    Hit.Item = Fragment.Id; Hit.ImpactPoint = Fragment.Location; Hit.Location = Fragment.Location;
    Context.AddHitResult(Hit);
    UMyAbilitySystemLibrary::SetIsBlockedHit(Context, bBlock);
    FGameplayEffectSpec Spec(GetDefault<UPureMassIncomingDamageEffect>(), Context, 1.f);
    Spec.SetSetByCallerMagnitude(UPureMassIncomingDamageEffect::GetDamageTag(), Damage);
    ASC->ApplyGameplayEffectSpecToSelf(Spec);
}

void UPureMassSubsystem::Move(FPureMassFragment& Fragment, FVector Delta)
{
    const UPureMassMonsterType* Type = Fragment.Type.Get();
    if (!Type || Delta.IsNearlyZero()) return;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(PureMassMovement), false);
    // Spell volumes are hit queries, never obstacles that depenetrate a monster capsule.
    FCollisionResponseParams Responses;
    Responses.CollisionResponse.SetResponse(ECC_Projectile, ECR_Ignore);
    FCollisionShape Shape = FCollisionShape::MakeCapsule(Type->Radius, Type->HalfHeight);
    FVector Position = Fragment.Location;
    FHitResult Hit;
    if (GetWorld()->SweepSingleByChannel(Hit, Position, Position + Delta, FQuat::Identity, ECC_Pawn, Shape, Params, Responses))
    {
        if (Hit.bStartPenetrating) Position += Hit.Normal * (Hit.PenetrationDepth + .5f);
        else Position += Delta * FMath::Max(0.f, Hit.Time - .001f);
        const FVector Slide = FVector::VectorPlaneProject(Delta * (1.f - Hit.Time), Hit.Normal);
        FHitResult SlideHit;
        if (GetWorld()->SweepSingleByChannel(SlideHit, Position, Position + Slide, FQuat::Identity, ECC_Pawn, Shape, Params, Responses))
            Position += Slide * FMath::Max(0.f, SlideHit.Time - .001f);
        else Position += Slide;
    }
    else Position += Delta;
    // Keep capsule bottoms on walkable world geometry without owning a movement component.
    FHitResult Ground;
    const FVector Foot = Position - FVector(0,0,Type->HalfHeight);
    if (GetWorld()->LineTraceSingleByChannel(Ground, Foot + FVector(0,0,45), Foot - FVector(0,0,90), ECC_WorldStatic, Params, Responses)
        && Ground.Normal.Z >= .65f)
    {
        const FVector Grounded(Position.X, Position.Y, Ground.ImpactPoint.Z + Type->HalfHeight + 1.f);
        FHitResult Vertical;
        if (!GetWorld()->SweepSingleByChannel(Vertical, Position, Grounded, FQuat::Identity, ECC_Pawn, Shape, Params, Responses)) Position = Grounded;
        else if (!Vertical.bStartPenetrating) Position += (Grounded - Position) * Vertical.Time;
    }
    Fragment.Velocity = (Position - Fragment.Location) / FMath::Max(DeltaTime, UE_SMALL_NUMBER);
    Fragment.Location = Position;
}

void UPureMassSubsystem::UpdateMonster(FPureMassFragment& Fragment)
{
    UPureMassMonsterType* Type = Fragment.Type.Get();
    if (!Type || Fragment.Health <= 0) return;
    Fragment.AttackRemaining = FMath::Max(0.f, Fragment.AttackRemaining - DeltaTime);
    Fragment.AttackVisualRemaining = FMath::Max(0.f, Fragment.AttackVisualRemaining - DeltaTime);
    Fragment.RootRemaining = FMath::Max(0.f, Fragment.RootRemaining - DeltaTime);
    Fragment.RootRecovery = FMath::Max(0.f, Fragment.RootRecovery - DeltaTime);
    if (Fragment.StatusRemaining > 0)
    {
        const float ActiveTime = FMath::Min(DeltaTime, Fragment.StatusRemaining);
        Fragment.StatusRemaining -= ActiveTime;
        DamageFragment(Fragment, Fragment.StatusDPS*ActiveTime, Fragment.StatusSource.Get());
        if (Fragment.Health <= 0) return;
    }
    if (Fragment.StatusRemaining <= 0)
    { Fragment.StatusDPS = 0; Fragment.StatusSlow = 1; Fragment.StatusSource.Reset(); }
    const float TerrainSlow = UpdateTerrain(Fragment);
    if (Fragment.Health <= 0) return;
    Fragment.Velocity = FVector::ZeroVector;
    Fragment.State = 0;
    APawn* Target = nullptr;
    double Nearest = TNumericLimits<double>::Max();
    for (const auto& Weak : Players)
        if (APawn* Player = Weak.Get(); Alive(Player))
        {
            const double Distance = FVector::DistSquared(Fragment.Location, Player->GetActorLocation());
            if (Distance < Nearest) { Nearest = Distance; Target = Player; }
        }
    if (!Target) { Publish(Fragment); return; }
    const FVector Goal = Target->GetActorLocation();
    if (Nearest <= FMath::Square(FinitePositive(Type->AttackRange)))
    {
        FHitResult Hit;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(PureMassAttack), false, Target);
        if (!GetWorld()->LineTraceSingleByChannel(Hit, Fragment.Location, Goal, ECC_Visibility, Params))
        {
            if (Fragment.AttackRemaining <= 0)
            {
                Fragment.AttackRemaining = FMath::Max(.1f, FinitePositive(Type->AttackPeriod, 1.5f));
                Fragment.AttackVisualRemaining = FMath::Min(.35f, Fragment.AttackRemaining*.6f);
                AttackPlayer(Fragment, Target);
            }
            Fragment.State = Fragment.AttackVisualRemaining > 0 ? 2 : 0;
            Publish(Fragment); return;
        }
        // Range alone is insufficient: a blocked target still requires a path around the obstacle.
    }
    if (Fragment.RootRemaining > 0) { Publish(Fragment); return; }
    const float Now = GetWorld()->GetTimeSeconds();
    const bool bNeedsPath = Now >= Fragment.NextPathTime
        || (Goal - Fragment.PathGoal).SizeSquared2D() > FMath::Square(200.f);
    if (bNeedsPath && PathsRemaining > 0)
    {
        --PathsRemaining;
        Fragment.NextPathTime = Now + .6f + .02f*(Fragment.Id % 11);
        Fragment.PathGoal = Goal;
        Fragment.Path.Reset(); Fragment.PathPoint = 0;
        if (UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
        {
            FNavAgentProperties Agent;
            Agent.AgentRadius = Type->Radius; Agent.AgentHeight = Type->HalfHeight*2;
            const FVector StartFoot = Fragment.Location - FVector(0,0,Type->HalfHeight);
            if (const ANavigationData* Data = Nav->GetNavDataForProps(Agent, StartFoot))
            {
                FNavLocation EndPoint;
                if (Nav->ProjectPointToNavigation(Goal, EndPoint, FVector(150,150,500), Data))
                {
                    FPathFindingQuery Query(this, *Data, StartFoot, EndPoint.Location);
                    const FPathFindingResult Result = Nav->FindPathSync(Agent, Query);
                    if (Result.IsSuccessful() && Result.Path.IsValid())
                        for (const FNavPathPoint& Point : Result.Path->GetPathPoints())
                            Fragment.Path.Add(Point.Location + FVector(0,0,Type->HalfHeight + 1.f));
                }
            }
        }
    }
    while (Fragment.Path.IsValidIndex(Fragment.PathPoint)
        && (Fragment.Path[Fragment.PathPoint] - Fragment.Location).SizeSquared2D() < FMath::Square(35.f)) ++Fragment.PathPoint;
    // A failed/no-nav path is a stopped entity, never a through-wall direct chase.
    if (Fragment.Path.IsValidIndex(Fragment.PathPoint))
    {
        FVector Desired = (Fragment.Path[Fragment.PathPoint] - Fragment.Location).GetSafeNormal2D();
        FVector Separation = FVector::ZeroVector;
        for (const uint64 Id : Grid.Query(Fragment.Location, Type->Radius + LargestRadius + 40))
        {
            if (Id == uint64(Fragment.Id)) continue;
            const FPureMassView* Other = Views.Find(int32(Id));
            if (!Other || !Other->Type) continue;
            FVector Offset = Fragment.Location - Other->Location; Offset.Z = 0;
            const float Distance = Offset.Size();
            const float Clearance = Type->Radius + Other->Type->Radius + 10;
            if (Distance < Clearance)
            {
                if (Distance < .1f)
                    Offset = FVector(Fragment.Id < Other->Id ? -1 : 1, 0, 0);
                Separation += Offset.GetSafeNormal() * (1.f - FMath::Min(Distance / Clearance, 1.f));
            }
        }
        Desired = (Desired + Separation*1.5f).GetSafeNormal2D();
        const float Speed = FinitePositive(Type->Speed)*FMath::Min(TerrainSlow, Fragment.StatusSlow);
        const float DistanceToCorner = FVector::Dist2D(Fragment.Location, Fragment.Path[Fragment.PathPoint]);
        Move(Fragment, Desired*FMath::Min(Speed*DeltaTime, DistanceToCorner));
        if (!Fragment.Velocity.IsNearlyZero(1.f)) Fragment.State = 1;
    }
    Publish(Fragment);
}
void UPureMassSubsystem::FinishUpdate()
{
    if (!Mass || !IsAuthority()) return;
    FMassEntityManager& Manager = Mass->GetMutableEntityManager();
    for (int32 Id : Dead)
    {
        FMassEntityHandle Handle;
        if (Entities.RemoveAndCopyValue(Id, Handle) && Manager.IsEntityValid(Handle))
        {
            if (Manager.IsProcessing()) Manager.Defer().DestroyEntity(Handle);
            else Manager.DestroyEntity(Handle);
        }
    }
    Dead.Reset();
}
void UPureMassSubsystem::Deinitialize()
{
    if (ProjectileSpawnHandle.IsValid()) GetWorld()->RemoveOnActorSpawnedHandler(ProjectileSpawnHandle);
    ProjectileSpawnHandle.Reset();
    LegacyFireBoltClass = nullptr;
    bEnabled = false;
    // Mass owns destruction. World teardown can destroy its manager before this subsystem.
    Mass = nullptr; Archetype = FMassArchetypeHandle();
    Entities.Reset(); Views.Reset(); Grid.Reset(); RetainedTypes.Reset();
    Players.Reset(); Terrain.Reset(); Dead.Reset();
    Super::Deinitialize();
}

