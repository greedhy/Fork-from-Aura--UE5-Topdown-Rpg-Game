# Batch 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build three composable mechanisms and six mixed Actor/Mass GAs with an isolated playable entry.
**Architecture:** New extension data, GA, world state service and runtime; reuse PureMassCombat, existing damage and surface APIs. New UI/catalog and map copies preserve existing files.
**Tech Stack:** UE 5.8, C++, GAS, Mass, Niagara, UE Python/SOMOLMCP.
**Spec:** `docs/superpowers/specs/2026-10-25-ga-prototypes-batch5-design.md` (approved 2026-10-25).

## Global Constraints

- Only new code/assets; preserve all existing working changes. No commits/push in this task.
- No per-monster Actor/ASC/collision proxy. Player/elite/boss use Actor/GAS.
- Server authority, one root cost, 64 nodes / 3 child levels, eight surfaces per cast.
- 3 prototypes + 6 compositions, learnable and unequipped, no user save changes.
- Use an opt-in map/GM/HUD/catalog copy when existing hard-coded UI requires it.

## Review Focus

- Dead target before detonation: last valid position, once only, no stale entity reuse.
- Two casters stacking same target: separate identity and ownership.
- Low frame rates: bounded catch-up; expiry beats boundary pulses.
- Mass navigation versus displacement: ordered processor, wall/ground checks and no snapback.
- Cancel/travel/hidden UI owner: cleanup and actual remote-visible effects/numbers.

### Task 1: Configuration and authoritative graph runtime

Files: new `AbilitySystem/PrototypeExtensions/ExtensionNode.h/.cpp`, `ExtensionRuntime.h/.cpp`, `ExtensionWorldSubsystem.h/.cpp`; new `Private/Tests/ExtensionTests.cpp`.
Interfaces: `AExtensionRuntime::Spawn(UPrototypeCastContext*, UExtensionNode*, FVector, FVector, FPureMassCombatTarget, int32)`; `UExtensionWorldSubsystem::AddStack(...)`; node kinds Attach, Stack, Displace, Projectile, Chain, Burst, Delay, Surface.
- [ ] Add fixtures and failing tests for target following, expiry pulses, transfer limit, stack threshold/isolation/expiry, wall-blocked projectile and once-only damage.
- [ ] Build and run focused native tests, record the initial missing behavior.
- [ ] Implement bounded validated graphs and shared cast context; graph event snapshots preserve target position even on lethal hit.
- [ ] Re-run focused tests until green; no changes to old runtime.

### Task 2: Controlled displacement and replicated presentation

Files: new `ExtensionDisplacementProcessor.h/.cpp`, extend new extension subsystem/runtime only.
Interfaces: `UExtensionWorldSubsystem::MoveMass(FPureMassFragment&, float)` called before `UPureMassProcessor`; `RequestDisplacement` returns a command token whose replacement/cancellation suppresses completion children.
- [ ] Add failing tests for distance cap, wall/ledge/floor constraints, immunity, replacement and expiration.
- [ ] Implement sweep + floor/navigation constraints; Actor CharacterMovement root motion; Mass ordered fragment update without changing original type or processor.
- [ ] Replicate active mark snapshots and node state; numeric layer labels, attachment position, impact effects; cap active marks and reclaim on death/travel.
- [ ] Verify focused tests and no per-enemy actors.

### Task 3: GA/input/menu entry and authoring

Files: new `ExtensionAbility.h/.cpp`, `ExtensionSpellTree.h/.cpp`, native tags; `Scripts/GA/Batch5/author_assets.py`, `validate_assets.py`.
Interfaces: GA holds `UExtensionNode* RootNode` and inherited fee config; uses existing mixed target task and server validation. New menu reads new catalog; new game mode points to copied catalog/HUD.
- [ ] Add failure checks for malformed/invalid targets and double target data/cost.
- [ ] Implement authority, cooldown, timeout, cancellation and short descriptions.
- [ ] Compile Editor/restart; create 9 GAs, isolated nodes/VFX and copied menu/GM/QA labyrinth.
- [ ] Read back all configs, tags, class defaults and untouched source asset hashes.

### Task 4: End-to-end validation and delivery

Files: new `Scripts/GA/Batch5/verify_pie.py`, validation/report scripts, usage guide.
- [ ] Run full `test_25d.` native suite, parse reports, resolve genuine failures.
- [ ] Drive all six compositions via remote Enhanced Input in two-client PIE; check mana, damage, marks, displacement and replication for both enemy forms.
- [ ] Check actual menu construction, 200 Mass scene, travel persistence and cleanup; inspect UI screenshot for damage/mark feedback.
- [ ] Independent whole-change review, fix material findings and retest impacted checks.
- [ ] Restore editor state and build settings; report playable map, names, tests and limitations.

## Execution ledger

Completion (2026-10-25): implemented and validated. Actual integration uses `ExtensionIntegration` (new HUD/player/game mode) rather than a second spell-tree implementation. See `docs/2026-10-25-ga-batch5-guide.md` and `Saved/GAAuthoring/Batch5/completion.json` for final behaviors, evidence, fixes, and restoration. All original source and reused asset hashes remain unchanged. No commit/push performed.

- User approved full scope and autonomous routine decisions on 2026-10-25.
- Native execution chosen to keep shared runtime interfaces consistent. Final fresh review required.
- Existing editor is bound to this dirty checkout and work depends on its uncommitted Mass fixes. Use a new branch in the same checkout, not an empty worktree that omits required fixes.
- Preflight: Tasks 1–3 share new node/runtime/subsystem interfaces; Task 4 consumes authored assets. No original public API changes required.
