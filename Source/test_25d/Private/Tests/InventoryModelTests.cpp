#include "Misc/AutomationTest.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ItemDefinition.h"
#include "Backpack/BackpackComponent.h"
#include "Game/MyGameInstance.h"

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
	UInventoryModel* Model = NewObject<UInventoryModel>();
	UItemDefinition* Potion = NewObject<UItemDefinition>();
	Potion->bStackable = false;

	Model->InitializeSlots(3);
	Model->TryAddItem(Potion, 3);
	Model->SetMaxSlots(2);

	TestEqual(TEXT("Capacity removes the tail slot"), Model->GetSlots().Num(), 2);
	TestFalse(TEXT("Existing slot zero is preserved"), Model->GetSlots()[0].IsEmpty());
	TestFalse(TEXT("Existing slot one is preserved"), Model->GetSlots()[1].IsEmpty());
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
	FGameInstanceOwnsOneBackpack,
	"test_25d.Inventory.GameInstanceOwnsOneBackpack",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGameInstanceOwnsOneBackpack::RunTest(const FString& Parameters)
{
	UMyGameInstance* GameInstance = NewObject<UMyGameInstance>();
	UBackpackComponent* FirstBackpack = GameInstance->GetBackpackComponent();
	UBackpackComponent* SecondBackpack = GameInstance->GetBackpackComponent();

	TestNotNull(TEXT("Game instance creates a backpack"), FirstBackpack);
	TestEqual(TEXT("Game instance returns the persistent backpack"), FirstBackpack, SecondBackpack);
	return true;
}

#endif
