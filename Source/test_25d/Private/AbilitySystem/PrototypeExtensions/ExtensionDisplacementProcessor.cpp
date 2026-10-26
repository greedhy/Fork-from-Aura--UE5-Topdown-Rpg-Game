#include "AbilitySystem/PrototypeExtensions/ExtensionDisplacementProcessor.h"
#include "AbilitySystem/PrototypeExtensions/ExtensionWorldSubsystem.h"
#include "PureMass/PureMassTypes.h"
#include "PureMass/PureMassProcessor.h"
#include "MassExecutionContext.h"
#include "Engine/World.h"
UExtensionDisplacementProcessor::UExtensionDisplacementProcessor():Query(*this)
{
    ProcessingPhase=EMassProcessingPhase::PostPhysics;
    ExecutionFlags=int32(EProcessorExecutionFlags::Server|EProcessorExecutionFlags::Standalone);
    bRequiresGameThreadExecution=true;
    ExecutionOrder.ExecuteBefore.Add(UPureMassProcessor::StaticClass()->GetFName());
}
void UExtensionDisplacementProcessor::ConfigureQueries(const TSharedRef<FMassEntityManager>&)
{ Query.AddRequirement<FPureMassFragment>(EMassFragmentAccess::ReadWrite); }
void UExtensionDisplacementProcessor::Execute(FMassEntityManager&,FMassExecutionContext& Context)
{
    auto* S=Context.GetWorld()->GetSubsystem<UExtensionWorldSubsystem>();
    if (!S) return;
    Query.ForEachEntityChunk(Context,[S](FMassExecutionContext& Chunk)
    { for (auto& F:Chunk.GetMutableFragmentView<FPureMassFragment>()) S->MoveMass(F,Chunk.GetDeltaTimeSeconds()); });
}
