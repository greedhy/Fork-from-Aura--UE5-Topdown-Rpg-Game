#include "AbilitySystem/PrototypeExtensions/ExtensionNode.h"
#include "Terrain/TerrainSurface.h"
namespace {
bool Validate(const UExtensionNode* N,int32 Depth,TSet<const UExtensionNode*>& Path)
{
    if (!N || Depth>3 || Path.Contains(N)) return false;
    for (float V:{N->Damage,N->DamagePerLevel,N->Range,N->Radius,N->Duration,N->Period,N->Speed,N->CollisionRadius,N->ManaCost,N->Cooldown,N->ArmDelay,N->TransferRadius,N->StackLifetime,N->DetonationDelay,N->MoveDistance,N->SafeDistance,N->DamageFalloff})
        if (!FMath::IsFinite(V) || V<0) return false;
    if (N->Duration<.1f || N->Duration>60 || N->Period<.1f || N->Range<1 || N->Radius<1 || N->Speed<1 || N->CollisionRadius<1
        || N->Count<1 || N->Count>16 || N->MaxTransfers<0 || N->MaxTransfers>16 || N->StackThreshold<1 || N->StackThreshold>16
        || N->StackLifetime<.1f || N->StackLifetime>60 || N->DetonationDelay>10 || N->MoveDistance>1200 || N->DamageFalloff>1
        || N->OnHit || N->OnPeriod || N->OnExpire) return false;
    using K=EExtensionKind;
    if (N->Behavior==K::Stack && (N->EffectId.IsNone() || !N->CompleteChild || N->HitChild || N->PeriodChild)) return false;
    if (N->Behavior==K::Attach && (!N->PeriodChild || N->HitChild)) return false;
    if (N->Behavior!=K::Attach && N->PeriodChild) return false;
    if ((N->Behavior==K::Delay || N->Behavior==K::Displace || N->Behavior==K::Surface) && N->HitChild) return false;
    if (N->Behavior==K::Delay && N->ArmDelay>N->Duration) return false;
    if (N->Behavior==K::Surface && !N->SurfaceClass) return false;
    for (auto& Pair:N->ActorTagMovementScale) if (!FMath::IsFinite(Pair.Value) || Pair.Value<0 || Pair.Value>1) return false;
    Path.Add(N);
    for (auto* Child:{N->HitChild.Get(),N->PeriodChild.Get(),N->CompleteChild.Get()}) if (Child && !Validate(Child,Depth+1,Path)) return false;
    Path.Remove(N); return true;
}
}
bool UExtensionNode::ValidateGraph() const { TSet<const UExtensionNode*> Path; return Validate(this,0,Path); }
