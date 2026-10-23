#include "AbilitySystem/Prototypes/AbilityPrototype.h"
#include "AbilitySystem/Data/OrbitingFireBoltConfig.h"
#include "NativeGameplayTags.h"
#include "Terrain/TerrainSurface.h"

#define PROTOTYPE_TAG(Name) \
UE_DEFINE_GAMEPLAY_TAG_STATIC(Ability##Name, "Abilities.Prototype." #Name); \
UE_DEFINE_GAMEPLAY_TAG_STATIC(Cooldown##Name, "Cooldown.Prototype." #Name);
PROTOTYPE_TAG(Projectile)
PROTOTYPE_TAG(Multishot)
PROTOTYPE_TAG(Burst)
PROTOTYPE_TAG(Beam)
PROTOTYPE_TAG(Surface)
PROTOTYPE_TAG(Orbit)
PROTOTYPE_TAG(Field)
PROTOTYPE_TAG(Trap)
PROTOTYPE_TAG(Homing)
PROTOTYPE_TAG(Piercing)
PROTOTYPE_TAG(Chain)
PROTOTYPE_TAG(Cone)
PROTOTYPE_TAG(Wave)
PROTOTYPE_TAG(Returning)
PROTOTYPE_TAG(Emitter)
PROTOTYPE_TAG(Delay)
PROTOTYPE_TAG(Ring)
PROTOTYPE_TAG(Line)
#undef PROTOTYPE_TAG
#define COMPOSITION_TAG(Name) \
UE_DEFINE_GAMEPLAY_TAG_STATIC(Ability##Name, "Abilities.Composition." #Name); \
UE_DEFINE_GAMEPLAY_TAG_STATIC(Cooldown##Name, "Cooldown.Composition." #Name);
COMPOSITION_TAG(FireSeed)
COMPOSITION_TAG(FrostFan)
COMPOSITION_TAG(BrambleMine)
COMPOSITION_TAG(StormSeal)
COMPOSITION_TAG(Aftershock)
COMPOSITION_TAG(FrostFault)
COMPOSITION_TAG(RippleMine)
COMPOSITION_TAG(HunterSentry)
#undef COMPOSITION_TAG

bool UAbilityPrototype::IsValidConfiguration() const
{
    for (float Value : {ManaCost, ManaPerSecond, Cooldown, Range, Radius, Duration, Period,
        Damage, DamagePerLevel, SpreadDegrees, Speed, CollisionRadius, ArmDelay, HomingTurnRate, DamageFalloff,
        InnerRadius, Width, ShapeHalfHeight})
        if (!FMath::IsFinite(Value) || Value < 0.f) return false;
    return static_cast<uint8>(Kind) <= static_cast<uint8>(EAbilityPrototypeKind::Line)
        && HomingTurnRate >= 1.f && HomingTurnRate <= 720.f && DamageFalloff <= 1.f
        && (Kind < EAbilityPrototypeKind::Homing || Kind == EAbilityPrototypeKind::Emitter || !OnPeriod)
        && (Kind != EAbilityPrototypeKind::Emitter || (OnPeriod && !OnHit))
        && (Kind != EAbilityPrototypeKind::Delay || (OnExpire && !OnHit && ArmDelay >= .1f && ArmDelay <= Duration))
        && (Kind != EAbilityPrototypeKind::Ring || InnerRadius < Radius)
        && (Kind != EAbilityPrototypeKind::Line || (Width > 0.f && Width <= 2000.f))
        && ((Kind != EAbilityPrototypeKind::Ring && Kind != EAbilityPrototypeKind::Line) || (ShapeHalfHeight > 0.f && ShapeHalfHeight <= 1000.f))
        && (Kind != EAbilityPrototypeKind::Cone || (SpreadDegrees > 0.f && SpreadDegrees <= 180.f))
        && Range > 0.f && Range <= 10000.f && Radius > 0.f && Radius <= 3000.f
        && Duration >= .1f && Duration <= 60.f && Period >= .1f && Speed > 0.f && Speed <= 10000.f
        && CollisionRadius > 0.f && CollisionRadius <= 200.f && Count >= 1 && Count <= 16
        && SpreadDegrees <= 360.f && DamageType.IsValid() && (Cooldown == 0.f || CooldownTag.IsValid())
        && (Kind != EAbilityPrototypeKind::Surface || (SurfaceClass && !OnHit))
        && (Kind != EAbilityPrototypeKind::Orbit || (OrbitSettings && OrbitSettings->IsValidConfiguration()));
}

float UAbilityPrototype::DamageAtLevel(int32 Level) const
{
    return Damage + DamagePerLevel * FMath::Clamp(Level - 1, 0, 99);
}

bool UPrototypeCastContext::ReserveSpawn(int32 Depth)
{
    if (bCancelled || Depth < 0 || Depth > 3 || Spawned >= 64) return false;
    ++Spawned;
    return true;
}
