# World Pickup and Drop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a centralized Data Asset item catalog, data-driven automatic/interact pickup, and server-authoritative whole-stack drop.

**Architecture:** `DA_BackpackItemDefinitions` is the only static-item catalog. Existing stable `FPrimaryAssetId` values remain in Fast Array slots, persistence snapshots, and replicated pickup actors. Server code resolves IDs through the catalog; a player-dropped stack becomes a public runtime-`Interact` pickup before its source slot is cleared.

**Tech Stack:** Unreal Engine 5.8, C++20, Enhanced Input, UMG/MVVM, Unreal Automation Tests, replicated Actors, `FFastArraySerializer`.

**Spec:** `docs/superpowers/specs/2026-08-20-world-pickup-drop-design.md`

## Global Constraints

- Create exactly one catalog asset: `Content/BluePrints/DA/DA_BackpackItemDefinitions.uasset`.
- Slots and world actors replicate only stable IDs, quantities, and effective pickup mode.
- Only the server mutates backpack slots or world pickups.
- `ServerRequestDrop` accepts only a stable slot index and always drops the complete stack.
- A dropped item is immediately public but always effective `Interact`, even if its table entry is `Auto`.
- Never stage generated files or unrelated restored content.

---

### Task 1: Add central item catalog types

**Files:**
- Modify: `Source/test_25d/Public/Backpack/ItemDefinition.h`
- Modify: `Source/test_25d/Private/Backpack/ItemDefinition.cpp`
- Modify: `Source/test_25d/Private/Tests/InventoryModelTests.cpp`

**Interfaces:**
- `EPickupMode { Auto, Interact }`.
- `FBackpackItemDefEntry` has `FPrimaryAssetId ItemDefinitionId`, display name, icon, world mesh, pickup mode, stack flags/limit, usability, and use effect.
- `UBackpackItemDefinitions : UDataAsset` has `TArray<FBackpackItemDefEntry> Items` and `FindDefinition(const FPrimaryAssetId&)`.

- [ ] **Step 1: Write the failing catalog test.**

```cpp
UBackpackItemDefinitions* Definitions = NewObject<UBackpackItemDefinitions>();
FBackpackItemDefEntry Potion;
Potion.ItemDefinitionId = FPrimaryAssetId(TEXT("BackpackItem"), TEXT("HealthPotion"));
Potion.PickupMode = EPickupMode::Auto;
Definitions->Items.Add(Potion);
TestEqual(TEXT("Find returns the configured entry"), Definitions->FindDefinition(Potion.ItemDefinitionId)->PickupMode, EPickupMode::Auto);
TestNull(TEXT("Unknown ID is rejected"), Definitions->FindDefinition(FPrimaryAssetId(TEXT("BackpackItem"), TEXT("Missing"))));
```

- [ ] **Step 2: Run red.**

Run: `Automation RunTests test_25d.Inventory.ItemDefinitionCatalog`

Expected: compile failure because catalog types and lookup are absent.

- [ ] **Step 3: Implement the table.**

Replace the individual `UPrimaryDataAsset` definition with the table types. `FindDefinition` scans `Items`, returns a matching entry, and returns `nullptr` for invalid or missing IDs. Static entries never contain runtime quantity.

- [ ] **Step 4: Run green and commit.**

Run: `Automation RunTests test_25d.Inventory.ItemDefinitionCatalog`

```powershell
git add Source/test_25d/Public/Backpack/ItemDefinition.h Source/test_25d/Private/Backpack/ItemDefinition.cpp Source/test_25d/Private/Tests/InventoryModelTests.cpp
git commit -m "feat: add backpack item definition catalog"
```

### Task 2: Resolve inventory and pickups through catalog IDs

**Files:**
- Modify: `Source/test_25d/Public/Backpack/InventoryModel.h`
- Modify: `Source/test_25d/Private/Backpack/InventoryModel.cpp`
- Modify: `Source/test_25d/Public/Backpack/BackpackComponent.h`
- Modify: `Source/test_25d/Private/Backpack/BackpackComponent.cpp`
- Modify: `Source/test_25d/Public/Backpack/WorldPickup.h`
- Modify: `Source/test_25d/Private/Backpack/WorldPickup.cpp`
- Modify: `Source/test_25d/Private/Tests/InventoryModelTests.cpp`

**Interfaces:**
- `UBackpackComponent::SetItemDefinitions(UBackpackItemDefinitions*)`.
- `FInventoryAddResult UBackpackComponent::TryAddItem(FPrimaryAssetId ItemDefinitionId, int32 Quantity)`.
- `AWorldPickup::InitializePickup(FPrimaryAssetId ItemDefinitionId, int32 Quantity, EPickupMode EffectiveMode)`.

- [ ] **Step 1: Write failing catalog-backed stack tests.**

```cpp
Component->SetItemDefinitions(Definitions);
TestTrue(TEXT("Known catalog ID adds"), Component->TryAddItem(PotionId, 3).bSucceeded);
TestEqual(TEXT("Catalog stack limit is obeyed"), Component->GetInventoryModel()->GetSlots()[0].Quantity, 2);
TestFalse(TEXT("Unknown ID is rejected"), Component->TryAddItem(UnknownId, 1).bSucceeded);
```

- [ ] **Step 2: Run red.**

Run: `Automation RunTests test_25d.Inventory.CatalogBackedSlots`

Expected: compile failure because the current add path still accepts `UItemDefinition*`.

- [ ] **Step 3: Refactor inventory resolution.**

Put the shared table on `UBackpackComponent`; remove `UInventoryModel`'s `TMap<FPrimaryAssetId, UItemDefinition*>`. Add, use, pickup, replication projection, and persistence resolve static data from the table while models retain only stable slots.

- [ ] **Step 4: Refactor `AWorldPickup`.**

Replace its replicated object pointer with `FPrimaryAssetId ItemDefinitionId` and add replicated effective `EPickupMode`. Normal spawners initialize from the table entry; drops explicitly pass `Interact`. Consume only the accepted quantity.

- [ ] **Step 5: Run green and commit.**

Run: `Automation RunTests test_25d.Inventory`

```powershell
git add Source/test_25d/Public/Backpack/InventoryModel.h Source/test_25d/Private/Backpack/InventoryModel.cpp Source/test_25d/Public/Backpack/BackpackComponent.h Source/test_25d/Private/Backpack/BackpackComponent.cpp Source/test_25d/Public/Backpack/WorldPickup.h Source/test_25d/Private/Backpack/WorldPickup.cpp Source/test_25d/Private/Tests/InventoryModelTests.cpp
git commit -m "refactor: resolve backpack items through catalog"
```

### Task 3: Implement automatic pickup and transactional public drop

**Files:**
- Modify: `Source/test_25d/Public/Backpack/InventoryModel.h`
- Modify: `Source/test_25d/Private/Backpack/InventoryModel.cpp`
- Modify: `Source/test_25d/Public/Backpack/BackpackComponent.h`
- Modify: `Source/test_25d/Private/Backpack/BackpackComponent.cpp`
- Modify: `Source/test_25d/Public/Backpack/WorldPickup.h`
- Modify: `Source/test_25d/Private/Backpack/WorldPickup.cpp`
- Modify: `Source/test_25d/Public/Player/MyPlayerController.h`
- Modify: `Source/test_25d/Private/Player/MyPlayerController.cpp`
- Modify: `Source/test_25d/Private/Tests/InventoryModelTests.cpp`

**Interfaces:**
- `FInventoryAddResult AWorldPickup::TryAutoPickup(APawn*)`.
- `bool UInventoryModel::RemoveCompleteStackAt(int32, FInventorySlot&)`.
- `bool UBackpackComponent::TryDropCompleteStackAt(int32, const FTransform&, AWorldPickup*&)`.
- `AMyPlayerController::ServerRequestDrop(int32 SlotIndex)`.

- [ ] **Step 1: Write failing behavior tests.**

```cpp
AutoPickup->InitializePickup(PotionId, 2, EPickupMode::Auto);
TestEqual(TEXT("Auto overlap accepts stack"), AutoPickup->TryAutoPickup(ServerPawn).AcceptedQuantity, 2);
DroppedPickup->InitializePickup(PotionId, 3, EPickupMode::Interact);
TestEqual(TEXT("Dropped auto item is interaction only"), DroppedPickup->GetEffectivePickupMode(), EPickupMode::Interact);
TestTrue(TEXT("Remove full stable stack"), Model->RemoveCompleteStackAt(0, DroppedSlot));
```

Also test deterministic failed spawn leaves inventory unchanged and another player can immediately interaction-pick up the drop.

- [ ] **Step 2: Run red.**

Run: `Automation RunTests test_25d.Inventory.AutoPickup; Automation RunTests test_25d.Inventory.DropCompleteStack`

Expected: missing automatic pickup and complete-stack APIs.

- [ ] **Step 3: Implement automatic pickup.**

Add a query-only pawn-overlap sphere. Server-side effective `Auto` overlaps resolve the Pawn PlayerState backpack and reuse `TryPickup`; interaction mode ignores overlap. Partial capacity leaves exactly the unaccepted world quantity.

- [ ] **Step 4: Implement spawn-before-remove drop.**

Validate controller, Pawn, PlayerState, component, and slot. Deferred-spawn an `AWorldPickup` 120 units forward; initialize it with `Interact`; finish spawn; then clear the complete slot, synchronize the Fast Array, and broadcast persistence state. On any spawn/init failure return false before removal.

- [ ] **Step 5: Run green and commit.**

Run: `Automation RunTests test_25d.Inventory`

```powershell
git add Source/test_25d/Public/Backpack/InventoryModel.h Source/test_25d/Private/Backpack/InventoryModel.cpp Source/test_25d/Public/Backpack/BackpackComponent.h Source/test_25d/Private/Backpack/BackpackComponent.cpp Source/test_25d/Public/Backpack/WorldPickup.h Source/test_25d/Private/Backpack/WorldPickup.cpp Source/test_25d/Public/Player/MyPlayerController.h Source/test_25d/Private/Player/MyPlayerController.cpp Source/test_25d/Private/Tests/InventoryModelTests.cpp
git commit -m "feat: add automatic pickup and public stack drops"
```

### Task 4: Bind `E`, UI, and the catalog asset

**Files:**
- Modify: `Source/test_25d/Public/Player/MyPlayerController.h`
- Modify: `Source/test_25d/Private/Player/MyPlayerController.cpp`
- Modify: `Source/test_25d/Public/UI/ViewModel/MVVM_Backpack.h`
- Modify: `Source/test_25d/Private/UI/ViewModel/MVVM_Backpack.cpp`
- Create: `Content/BluePrints/DA/DA_BackpackItemDefinitions.uasset`
- Create: `Content/BluePrints/Input/InputActions/IA_Interact.uasset`
- Modify: `Content/BluePrints/Input/IMC_PlayerContext.uasset`
- Modify: `Content/BluePrints/UI/Backpack/WBP_Backpack.uasset`
- Modify: `Content/BluePrints/UI/Backpack/WBP_BackpackSlot.uasset`
- Modify: `README.md`

**Interfaces:**
- `AMyPlayerController::InteractWithFocusedPickup()` submits existing `ServerRequestPickup` for a nearby effective-`Interact` actor.
- `UMVVM_Backpack::RequestDrop(int32)` calls `ServerRequestDrop` for local controllers.

- [ ] **Step 1: Write failing request tests.**

```cpp
ViewModel->Initialize(Model, LocalController);
ViewModel->RequestDrop(0);
TestEqual(TEXT("Forwards only stable slot"), LocalController->LastRequestedDropSlot, 0);
TestFalse(TEXT("Invalid slot cannot drop"), Component->TryDropCompleteStackAt(99, FTransform(), Pickup));
```

- [ ] **Step 2: Run red.**

Run: `Automation RunTests test_25d.Inventory.ViewModelDropRequest`

Expected: drop forwarding does not exist.

- [ ] **Step 3: Implement request paths.**

Track a nearby effective-`Interact` pickup locally and bind `E` to `IA_Interact`; only send its actor reference via `ServerRequestPickup`. Change `RequestDrop` to use the local-controller RPC path instead of the unused local delegate.

- [ ] **Step 4: Configure the one catalog asset and widgets in Unreal Editor.**

Create `DA_BackpackItemDefinitions` with exactly `BackpackItem:HealthPotion` (Auto, stack 10, existing potion icon/mesh/use effect) and `BackpackItem:QuestRelic` (Interact, stack 1, existing crystal icon/mesh, no use effect). Assign the table to backpack and world-pickup defaults. Create digital `IA_Interact`, bind `E`, add a Drop button disabled for empty slots, and show an `E` prompt only for focused interaction pickups.

- [ ] **Step 5: Run matrix, document, and commit.**

Run: `Automation RunTests test_25d.Inventory`

In two-client listen-server PIE: auto-pick HealthPotion; require `E` for QuestRelic; drop HealthPotion; verify no automatic recollection; have player two press `E`. Repeat public drop with a dedicated server. Record commands in `README.md`.

```powershell
git add Source/test_25d/Public/Player/MyPlayerController.h Source/test_25d/Private/Player/MyPlayerController.cpp Source/test_25d/Public/UI/ViewModel/MVVM_Backpack.h Source/test_25d/Private/UI/ViewModel/MVVM_Backpack.cpp Source/test_25d/Private/Tests/InventoryModelTests.cpp Content/BluePrints/DA/DA_BackpackItemDefinitions.uasset Content/BluePrints/Input/InputActions/IA_Interact.uasset Content/BluePrints/Input/IMC_PlayerContext.uasset Content/BluePrints/UI/Backpack/WBP_Backpack.uasset Content/BluePrints/UI/Backpack/WBP_BackpackSlot.uasset README.md
git commit -m "feat: configure catalog-driven world item interaction"
```
