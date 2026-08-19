# Networked Backpack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a server-authoritative, replicated backpack that survives Pawn replacement, travel, and reconnect.

**Architecture:** `AMyPlayerState` owns the server backpack component and replicated stable slots. `AMyPlayerController` exposes intent-only server RPCs; the server validates then mutates inventory and applies effects to the current Pawn ASC. Persistence is behind a server-side interface keyed by player identity.

**Tech Stack:** Unreal Engine 5.8, C++20, Gameplay Ability System, UMG/MVVM, Unreal Automation Tests, `FFastArraySerializer`.

**Spec:** `docs/superpowers/specs/2026-08-19-networked-backpack-design.md`

## Global Constraints

- Server state is authoritative; no client code mutates slots, quantity, or capacity.
- `GameInstance` holds no backpack state.
- Replicate stable slots with `FFastArraySerializer`; never replicate UI/ViewModel objects.
- Only decrement a usable item after the Gameplay Effect applies successfully.
- Support listen-server and dedicated-server tests; reject duplicate active player identities.

---

### Task 1: Move ownership from GameInstance to PlayerState

**Files:**
- Modify: `Public/Player/MyPlayerState.h`, `Private/Player/MyPlayerState.cpp`
- Modify: `Public/Backpack/BackpackComponent.h`, `Private/Backpack/BackpackComponent.cpp`
- Modify: `Public/Private/Game/MyGameInstance.*`, `Public/Private/Character/PlayerCharacter.*`
- Modify: `Private/Tests/InventoryModelTests.cpp`

**Produces:** `AMyPlayerState::GetBackpackComponent() const`; a component created in the PlayerState constructor and initialized once on the server; `APlayerCharacter` resolves its current PlayerState backpack.

- [ ] **Step 1: Write the failing ownership test.**

```cpp
AMyPlayerState* State = NewObject<AMyPlayerState>();
TestNotNull(TEXT("PlayerState owns backpack"), State->GetBackpackComponent());
TestNull(TEXT("GameInstance has no backpack API"), nullptr);
```

- [ ] **Step 2: Build the editor target; expect the PlayerState getter to be missing.**
- [ ] **Step 3: Create `BackpackComponent` as a default subobject in `AMyPlayerState`; remove `UMyGameInstance::GetBackpackComponent`, its UPROPERTY, and PlayerCharacter's GameInstance accessor.**
- [ ] **Step 4: Make `APlayerCharacter` resolve `GetPlayerState<AMyPlayerState>()->GetBackpackComponent()` only after possession/replication.**
- [ ] **Step 5: Run `Automation RunTests test_25d.Inventory`; expect PASS, then commit `feat: move backpack ownership to player state`.**

### Task 2: Create replicated stable-slot state

**Files:**
- Create: `Public/Backpack/ReplicatedInventory.h`, `Private/Backpack/ReplicatedInventory.cpp`
- Modify: `Public/Private/Backpack/BackpackComponent.*`, `Public/Private/Backpack/InventoryModel.*`
- Modify: `Private/Tests/InventoryModelTests.cpp`

**Produces:** `FReplicatedInventorySlot`, `FReplicatedInventoryList : FFastArraySerializer`, `UBackpackComponent::OnRep_Inventory()`, and server-only `TryAddItem`, `SwapSlots`, and `UseItemAt` mutations.

- [ ] **Step 1: Write failing tests for a changed stable slot being marked dirty and a client-side mutation being rejected.**

```cpp
TestTrue(TEXT("Server marks changed slot dirty"), ReplicatedSlots.Items[0].ReplicationID != INDEX_NONE);
TestFalse(TEXT("Client cannot mutate inventory"), Component->TryAddItem(nullptr, 1).bSucceeded);
```

- [ ] **Step 2: Build; expect missing replicated-list types and server guard.**
- [ ] **Step 3: Implement `FFastArraySerializer` slots containing `FPrimaryAssetId` and quantity; call `MarkItemDirty` only after successful server mutations and use `OnRep` to refresh the local model/VM.**
- [ ] **Step 4: Add `GetLifetimeReplicatedProps`, set the component replicated, and replicate only the slot list, capacity, and revision.**
- [ ] **Step 5: Run the inventory suite and two-client PIE replication test; commit `feat: replicate authoritative backpack slots`.**

### Task 3: Add validated server requests and use effects

**Files:**
- Modify: `Public/Private/Player/MyPlayerController.*`
- Modify: `Public/Private/Backpack/BackpackComponent.*`, `Public/Backpack/ItemDefinition.h`
- Modify: `Public/Private/UI/ViewModel/MVVM_Backpack.*`
- Modify: `Private/Tests/InventoryModelTests.cpp`

**Produces:** `ServerRequestPickup(AActor*)`, `ServerRequestSwap(int32,int32)`, `ServerRequestUse(int32)`, and `UItemDefinition::UseEffect`.

- [ ] **Step 1: Write failing tests for invalid slot rejection and an unusable/effectless item not being consumed.**

```cpp
TestFalse(TEXT("Invalid use does not consume"), Component->TryUseItemForPawn(99, Pawn));
TestEqual(TEXT("Failed effect retains stack"), Component->GetSlot(0).Quantity, 1);
```

- [ ] **Step 2: Build; expect the RPC and `UseEffect` members to be missing.**
- [ ] **Step 3: Add reliable server RPCs on `AMyPlayerController`; resolve its PlayerState and current Pawn on the server. Validate indexes, world pickup distance/authority, and Pawn ASC.**
- [ ] **Step 4: Add `TSubclassOf<UGameplayEffect> UseEffect`; create an ASC effect spec with the current Pawn as target, apply it, then decrement only if application succeeds.**
- [ ] **Step 5: Make MVVM send requests through the local controller only; run automation and listen-server PIE; commit `feat: validate server backpack requests`.**

### Task 4: Preserve state through death, travel, and reconnect

**Files:**
- Create: `Public/Backpack/BackpackPersistence.h`, `Private/Backpack/BackpackPersistence.cpp`
- Modify: `Public/Private/Game/MyGameModeBase.*`, `Public/Private/Player/MyPlayerState.*`
- Modify: `Private/Tests/InventoryModelTests.cpp`

**Produces:** `FBackpackSnapshot`, `IBackpackPersistenceProvider::{Load,Save,AcquireSessionLock,ReleaseSessionLock}`, and PlayerState snapshot import/export.

- [ ] **Step 1: Write failing tests for snapshot round-trip, restored slot order, and duplicate-lock rejection.**
- [ ] **Step 2: Implement snapshot conversion from replicated slots without serializing ViewModels or actors.**
- [ ] **Step 3: Implement a server-local SaveGame provider keyed by validated player ID; load after login lock acquisition, save after mutation/disconnect/travel, and release after final save.**
- [ ] **Step 4: Hook PlayerState travel copying/restoration and GameMode login/logout; replacement Pawns use the unchanged PlayerState component.**
- [ ] **Step 5: Run death/respawn, seamless travel, ordinary travel, reconnect, and duplicate-login PIE cases; commit `feat: persist networked backpack state`.**

### Task 5: Configure assets and document verification

**Files:**
- Modify: `Content/Items/DA_Item_HealthPotion.uasset`, `Content/Items/DA_Item_ManaPotion.uasset`
- Modify: backpack UI assets and `README.md`

- [ ] **Step 1: Assign `UseEffect` to health and mana definitions; preserve stack and pickup settings.**
- [ ] **Step 2: Bind UI only to replicated typed VM values and controller request APIs; no Blueprint graph mutates slots.**
- [ ] **Step 3: Record editor build, automation command, listen-server test, and dedicated-server test commands in README.**
- [ ] **Step 4: Run `Automation RunTests test_25d.Inventory`, listen-server two-client PIE, and dedicated-server client connection tests; commit `docs: verify networked backpack`.**
