#pragma once
#include "CoreMinimal.h"
#include "MassProcessor.h"
#include "MassEntityQuery.h"
#include "ExtensionDisplacementProcessor.generated.h"
UCLASS()
class TEST_25D_API UExtensionDisplacementProcessor : public UMassProcessor
{
    GENERATED_BODY()
public:
    UExtensionDisplacementProcessor();
protected:
    virtual void ConfigureQueries(const TSharedRef<FMassEntityManager>& Manager) override;
    virtual void Execute(FMassEntityManager& Manager,FMassExecutionContext& Context) override;
private:
    FMassEntityQuery Query;
};
