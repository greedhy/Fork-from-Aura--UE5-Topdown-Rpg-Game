#include "Misc/AutomationTest.h"
#include "Backpack/InventoryModel.h"
#include "Backpack/ItemDefinition.h"

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

#endif
