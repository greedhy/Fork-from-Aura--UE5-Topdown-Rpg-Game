#pragma once

#include "CoreMinimal.h"
#include "Character/PlayerCharacter.h"
#include "PureMassPlayerCharacter.generated.h"

/** Isolated test-map pawn: fresh Mass ability loadout, without importing/writing Actor ability saves. */
UCLASS()
class TEST_25D_API APureMassPlayerCharacter : public APlayerCharacter
{
    GENERATED_BODY()
public:
    virtual void PossessedBy(AController* NewController) override;
    virtual void Die(const FVector& DeathImpulse) override;
    virtual int32 GetPlayerLevel_Implementation() override;
    virtual void SaveProgress_Implementation(const FName& CheckpointTag) override {}
protected:
    virtual void InitAbilityActorInfo() override;
private:
    int32 LastKnownLevel = 1;
};
