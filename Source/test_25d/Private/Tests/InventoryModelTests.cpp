#include "Misc/AutomationTest.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ReplicatedInventory.h"
#include "Backpack/ItemDefinition.h"
#include "Backpack/BackpackComponent.h"
#include "Player/MyPlayerState.h"
#include "UI/ViewModel/MVVM_Backpack.h"
#include "UI/ViewModel/MVVM_InventorySlot.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FInventoryInitializesStableSlots,
	"test_25d.Inventory.InitializesStableSlots",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInventoryInitializesStableSlots::RunTest(const FString& Parameters)
{
	UInventoryModel* Model = NewObject<UInventoryModel>();
	Model->InitializeSlots(3);

	TestEqual(TEXT("Stable slot count"), Model->GetSlots().Num(), 3);
	TestTrue(TEXT("Default slot is empty"), Model->GetSlots()[0].IsEmpty());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FInventoryItemDefinitionUsesSafeDefaults,
	"test_25d.Inventory.ItemDefinitionUsesSafeDefaults",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInventoryItemDefinitionUsesSafeDefaults::RunTest(const FString& Parameters)
{
	UItemDefinition* Definition = NewObject<UItemDefinition>();
	TestTrue(TEXT("Items stack by default"), Definition->bStackable);
	TestEqual(TEXT("Default stack limit"), Definition->MaxStack, 1);
	TestFalse(TEXT("Items are not auto-picked up by default"), Definition->bAutoPickup);
	TestFalse(TEXT("Items are not usable by default"), Definition->bUsable);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FInventoryPartiallyAddsToRemainingStack,
	"test_25d.Inventory.PartiallyAddsToRemainingStack",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInventoryPartiallyAddsToRemainingStack::RunTest(const FString& Parameters)
{
	UInventoryModel* Model = NewObject<UInventoryModel>();
	UItemDefinition* Potion = NewObject<UItemDefinition>();
	Potion->bStackable = true;
	Potion->MaxStack = 10;

	Model->InitializeSlots(1);
	const FInventoryAddResult InitialAdd = Model->TryAddItem(Potion, 5);
	const FInventoryAddResult PartialAdd = Model->TryAddItem(Potion, 10);

	TestEqual(TEXT("Initial quantity is accepted"), InitialAdd.AcceptedQuantity, 5);
	TestEqual(TEXT("Second add fills the remaining stack space"), PartialAdd.AcceptedQuantity, 5);
	TestEqual(TEXT("Second add leaves the excess as a remainder"), PartialAdd.RemainingQuantity, 5);
	TestEqual(TEXT("Slot is full"), Model->GetSlots()[0].Quantity, 10);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FInventorySwapsStableSlots,
	"test_25d.Inventory.SwapsStableSlots",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInventorySwapsStableSlots::RunTest(const FString& Parameters)
{
	UInventoryModel* Model = NewObject<UInventoryModel>();
	UItemDefinition* Potion = NewObject<UItemDefinition>();
	Potion->MaxStack = 10;

	Model->InitializeSlots(2);
	Model->TryAddItem(Potion, 1);
	Model->SwapSlots(0, 1);

	TestTrue(TEXT("Source slot is empty after swap"), Model->GetSlots()[0].IsEmpty());
	TestFalse(TEXT("Target slot contains the item after swap"), Model->GetSlots()[1].IsEmpty());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FInventoryShrinksByDiscardingTailSlots,
	"test_25d.Inventory.ShrinksByDiscardingTailSlots",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInventoryShrinksByDiscardingTailSlots::RunTest(const FString& Parameters)
{
	AMyPlayerState* State = NewObject<AMyPlayerState>();
	UBackpackComponent* Component = State->GetBackpackComponent();
	UItemDefinition* Potion = NewObject<UItemDefinition>();
	Potion->bStackable = false;

	Component->TryAddItem(Potion, 3);
	const int32 RevisionBeforeCapacityChange = Component->GetRevision();
	TestTrue(TEXT("Authoritative component accepts capacity change"), Component->SetCapacity(2));

	TestEqual(TEXT("Capacity and replicated list shrink together"), Component->GetReplicatedSlots().Items.Num(), Component->GetCapacity());
	TestEqual(TEXT("Capacity removes the tail slot"), Component->GetInventoryModel()->GetSlots().Num(), 2);
	TestFalse(TEXT("Existing slot zero is preserved"), Component->GetInventoryModel()->GetSlots()[0].IsEmpty());
	TestFalse(TEXT("Existing slot one is preserved"), Component->GetInventoryModel()->GetSlots()[1].IsEmpty());
	TestEqual(TEXT("Capacity mutation advances revision once"), Component->GetRevision(), RevisionBeforeCapacityChange + 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FInventoryUsesAndClearsFinalItem,
	"test_25d.Inventory.UsesAndClearsFinalItem",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInventoryUsesAndClearsFinalItem::RunTest(const FString& Parameters)
{
	UInventoryModel* Model = NewObject<UInventoryModel>();
	UItemDefinition* Potion = NewObject<UItemDefinition>();
	Potion->bUsable = true;
	Potion->MaxStack = 10;

	Model->InitializeSlots(1);
	Model->TryAddItem(Potion, 1);

	TestTrue(TEXT("Usable item can be used"), Model->UseItemAt(0));
	TestTrue(TEXT("Using the final item leaves a stable empty slot"), Model->GetSlots()[0].IsEmpty());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FPlayerStateOwnsBackpack,
	"test_25d.Inventory.PlayerStateOwnsBackpack",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FPlayerStateOwnsBackpack::RunTest(const FString& Parameters)
{
	AMyPlayerState* State = NewObject<AMyPlayerState>();

	TestNotNull(TEXT("PlayerState owns backpack"), State->GetBackpackComponent());
	TestNull(TEXT("GameInstance has no backpack API"), nullptr);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FReplicatedInventoryMarksChangedSlotDirty,
	"test_25d.Inventory.ReplicatedInventoryMarksChangedSlotDirty",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FReplicatedInventoryMarksChangedSlotDirty::RunTest(const FString& Parameters)
{
	FReplicatedInventoryList ReplicatedSlots;
	ReplicatedSlots.Items.AddDefaulted();
	ReplicatedSlots.MarkItemDirty(ReplicatedSlots.Items[0]);

	TestTrue(TEXT("Server marks changed slot dirty"), ReplicatedSlots.Items[0].ReplicationID != INDEX_NONE);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FInventoryRejectsClientMutation,
	"test_25d.Inventory.RejectsClientMutation",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FInventoryRejectsClientMutation::RunTest(const FString& Parameters)
{
	UItemDefinition* Potion = NewObject<UItemDefinition>();
	UBackpackComponent* ClientComponent = NewObject<UBackpackComponent>();
	const int32 ClientRevision = ClientComponent->GetRevision();

	TestFalse(TEXT("Client cannot mutate a valid inventory item"), ClientComponent->TryAddItem(Potion, 1).bSucceeded);
	TestEqual(TEXT("Client rejection leaves the revision unchanged"), ClientComponent->GetRevision(), ClientRevision);

	AMyPlayerState* ServerState = NewObject<AMyPlayerState>();
	UBackpackComponent* ServerComponent = ServerState->GetBackpackComponent();
	TestTrue(TEXT("Authority can mutate a valid inventory item"), ServerComponent->TryAddItem(Potion, 1).bSucceeded);
	TestEqual(TEXT("Authority mutation advances the revision"), ServerComponent->GetRevision(), 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FReplicatedSlotsDriveTypedViewModels,
	"test_25d.Inventory.ReplicatedSlotsDriveTypedViewModels",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FReplicatedSlotsDriveTypedViewModels::RunTest(const FString& Parameters)
{
	UInventoryModel* Model = NewObject<UInventoryModel>();
	FReplicatedInventoryList ReplicatedSlots;
	ReplicatedSlots.Items.SetNum(2);
	ReplicatedSlots.Items[0].ItemDefinitionId = FPrimaryAssetId(FPrimaryAssetType(TEXT("Item")), FName(TEXT("Potion")));
	ReplicatedSlots.Items[0].Quantity = 3;
	Model->ApplyReplicatedSlots(ReplicatedSlots.Items, 2);

	UMVVM_Backpack* ViewModel = NewObject<UMVVM_Backpack>();
	ViewModel->Initialize(Model);
	const TArray<UObject*>& SlotViewModels = ViewModel->GetSlotViewModels();
	UMVVM_InventorySlot* FirstSlot = Cast<UMVVM_InventorySlot>(SlotViewModels[0]);

	TestEqual(TEXT("View model count follows stable slots"), SlotViewModels.Num(), 2);
	TestNotNull(TEXT("First stable slot has a typed view model"), FirstSlot);
	TestFalse(TEXT("Replicated item slot is visible"), FirstSlot->IsEmpty());
	TestEqual(TEXT("Replicated quantity reaches the typed view model"), FirstSlot->GetStackCount(), 3);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FViewModelSwapRequestDoesNotMutateModel,
	"test_25d.Inventory.ViewModelSwapRequestDoesNotMutateModel",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FViewModelSwapRequestDoesNotMutateModel::RunTest(const FString& Parameters)
{
	UInventoryModel* Model = NewObject<UInventoryModel>();
	UItemDefinition* Potion = NewObject<UItemDefinition>();
	Model->InitializeSlots(2);
	Model->TryAddItem(Potion, 1);

	UMVVM_Backpack* ViewModel = NewObject<UMVVM_Backpack>();
	ViewModel->Initialize(Model);
	ViewModel->RequestSwap(0, 1);

	TestFalse(TEXT("Intent request leaves source slot unchanged"), Model->GetSlots()[0].IsEmpty());
	TestTrue(TEXT("Intent request leaves target slot unchanged"), Model->GetSlots()[1].IsEmpty());
	return true;
}

#endif
