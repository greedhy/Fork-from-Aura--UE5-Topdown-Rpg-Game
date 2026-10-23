#pragma once

#include "CoreMinimal.h"
#include "MassEntityTypes.h"
#include "MonsterFragments.generated.h"

class AEnemyCharacter;

/** Server-only bridge. UObject access is restricted to the game-thread processor. */
USTRUCT()
struct TEST_25D_API FMonsterFragment : public FMassFragment
{
    GENERATED_BODY()
    TWeakObjectPtr<AEnemyCharacter> Actor;
    FVector Location = FVector::ZeroVector;
    FName RoomId;
    FName MonsterType;
    uint64 RegistrationId = 0;
    bool bActive = true;
};
