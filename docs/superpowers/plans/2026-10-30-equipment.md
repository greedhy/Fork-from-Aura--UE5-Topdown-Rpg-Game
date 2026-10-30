# Equipment Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. Track steps below.

**Goal:** Implement server-owned equipment using the existing backpack and one Infinite GE per item.
**Architecture:** PlayerState owns EquipmentComponent and ASC. Inventory instance IDs survive movement and a combined backpack/equipment snapshot. A restricted, reversible GE contract permits apply-first swaps without losing the old equipment on rejection.
**Tech Stack:** UE 5.8 C++, GAS, replicated components, Unreal automation.
**Spec:** docs/equipment-development-standard.md

## Global Constraints
- Server validates all mutations. No consumable behavior change for existing potions.
- Fixed modifiers, Infinite, non-periodic, no stacking; no arbitrary GE side effects in initial equipment assets.
- Preserve existing uncommitted work; no automatic commit of the user's staged assets.
- Death retains records; initialization after base attributes rebuilds missing effects.

## Review Focus
- Two identical item definitions must keep separate identities and effects.
- Failed GE application must preserve the old item and effect.
- Full backpack swaps use the vacated source slot; unequip fails safely.
- Repeated initialization/restoration must not multiply effects.
- Decreasing maximum resources clamps once after a swap, never heals.

### Task 1: Identity and storage
- [x] Add equipment behavior tests in Private/Tests/EquipmentTests.cpp, observe missing implementation.
- [x] Add ItemInstanceId to inventory, pickup and snapshot records, preserve it on moves.
- [x] Add equippable definition metadata and reject equipment in consumable use paths.

### Task 2: Equipment transactions
- [x] Add Public/Equipment/EquipmentComponent.h and Private/Equipment/EquipmentComponent.cpp.
- [x] Expose TryEquip(slot index, slot tag, expected instance, expected backpack revision, expected equipment revision), TryUnequip and ReconcileEffects.
- [x] Add replicated slot state, Blueprint RPC/UI hooks, authority/state validation and a shared inventory mutation lock.
- [x] Apply new GE before removing old; rollback new handle if rejected; commit records and notify once. Restrict GE configuration and clamp resources only at completion.
- [x] Test independent effects, stale requests, failed replacements and capacity handling.

### Task 3: Persistence and lifecycle
- [x] Extend FBackpackSnapshot with equipment records/revision, validate all records before import.
- [x] Wire PlayerState creation/export/import, existing persistence notification, and post-attribute character initialization.
- [x] Test old snapshots, duplicate instance rejection, restoration and effect reconciliation.

### Task 4: Verification and delivery
- [x] Build test_25dEditor Win64 Development using UE 5.8 Build.bat.
- [x] Run test_25d.Equipment and test_25d.Inventory automation; examine report counts and failures.
- [x] Review whole change; document asset configuration, UI integration and PIE checklist with actual verification status.

## Execution ledger
- Ruling: Implement inline in the current checkout because the specification and dependent project changes are uncommitted here. Do not move or discard them.
- Ruling: Slot tags are designer-configurable; no new fixed slot taxonomy. Expose Blueprint operations/events for the existing UI rather than guessing a new visual layout.
- Ruling: Apply new effect first, then remove the old effect. Reject non-reversible GE definitions; this avoids reapplying old effects when new applications are rejected.

- Verification: latest suffix DLL build succeeded. 191 project tests completed (100 success, 91 success with warnings), zero failures/not-run; six equipment tests passed. User PIE and content/UI authoring remain integration acceptance, not automated proof.
- Review fixes: atomic combined restore; external effect removal recovery; base-value progress serialization; equipment-before-travel-resource restore; pickup reentry lock.
