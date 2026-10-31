#pragma once
#include "CoreMinimal.h"
#include "Character/PlayerCharacter.h"

namespace PrototypeFacing
{
// Instant prototype casts have no montage window to consume a Motion Warping target.
// Called only after a successful authoritative cast; self casts retain their facing.
inline void Apply(AActor* Avatar, const FVector& Target, bool bTargetSelf)
{
    if (bTargetSelf || !IsValid(Avatar) || !Avatar->HasAuthority() ||
        !Avatar->IsA<APlayerCharacter>() || Target.ContainsNaN()) return;
    FVector Direction = Target - Avatar->GetActorLocation();
    Direction.Z = 0;
    if (Direction.IsNearlyZero() || Direction.ContainsNaN()) return;
    Avatar->SetActorRotation(FRotator(0, Direction.Rotation().Yaw, 0));
    Avatar->ForceNetUpdate();
}
}
