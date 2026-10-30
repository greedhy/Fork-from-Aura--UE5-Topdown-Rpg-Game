#pragma once

#include "CoreMinimal.h"
#include "PureMassEncounterTypes.generated.h"

UENUM(BlueprintType)
enum class EPureMassRemovalReason : uint8
{
    Killed,
    Recycled,
    Unexpected
};

/** Authority-only lifecycle notification. Callbacks may run during Mass processing. */
DECLARE_MULTICAST_DELEGATE_ThreeParams(FOnPureMassRemoved, int32, FName, EPureMassRemovalReason);
