# Pure Mass migration — additive implementation

User requirements: no per-monster Actor, including GAS adapters; entity combat interfaces; all work in NEW files and NEW assets. Existing source, configuration, maps, materials and ability assets are read-only. The baseline is Saved/PureMass/original-files.json (2440 files).

Implementation boundaries:
1. PureMassTypes / PureMassSubsystem / PureMassProcessor: real Mass fragments, stable IDs, spatial queries, navmesh paths, data capsules/world sweeps, damage/status/death/XP and player attacks. Server-authoritative. Only explicitly enabled worlds simulate.
2. PureMassCrowd: one replicated shared renderer, instanced skinned components per type, per-instance animation tracks, client interpolation. New cloned meshes/materials/animation-bank assets only.
3. PureMassAbility / PureMassRuntime / target task: isolated player GAS entry and entity combat targets, existing prototype configurations read-only. No hidden fallback to monster Actors.
4. PureMassGameMode / authoring scripts / copied map and ability assets: opt-in sandbox; existing gameplay remains untouched. Copy map via new_level_from_template. Remove old enemy actors/spawners ONLY from the copy. New mode references new configs/assets.
5. Build, native tests, standalone and two-client PIE, preservation audit and guide. Report observed evidence, not tool submission receipts.

Integration contract (positions are capsule centres): UPureMassSubsystem exposes Enable(), SpawnMonster(Type, Location, Room) -> int32, Resolve(Id, FPureMassView&) const, QueryRadius(Center, Radius)->TArray<int32>, Sweep(Start,End,Radius,OutTime)->int32, ApplyDamage(Id, FPureMassDamage)->float, GetSnapshots()->TArray<FPureMassView>. Views contain Id, Location, Velocity, Health, MaxHealth, State (0 idle/1 run/2 attack/3 dead), Type. Type holds mesh and provider plus movement/combat settings. Damage contains Source actor, Amount, DamageType and status fields. Dead IDs never reused. Client registry consumes shared snapshots; cannot mutate health.

Files in this plan can be edited while developing; files present before the baseline cannot. No commits or external publishing. Build artifacts and logs are generated outputs, not protected source/content.

Completed 2026-10-23: 25 new source/test files, isolated /Game/PureMass content, 26 copied GAs. build-9 succeeded; Tests-Final3 reports 107 passed/0 failed (47 pre-existing warnings). 43 asset, 23 two-client base, 14 two-client channel and 8 standalone assertions pass. Original 2440-file preservation audit passes. Review fixes include occluded-melee navigation, newborn orbit position, copied orbit visuals, isolated respawn and persistent HUD/ASC initialization. PIE additionally verified stable native incoming-damage/mana GE definitions and removed old-pawn attribute contexts before respawn. Editor left stopped on L_PureMassDungeon. Deferred boundaries are explicitly documented in docs/2026-10-23-pure-mass-guide.md (no old Actor GA auto-replacement, no actor-bound enemy HUD/debuff/montage migration, no population benchmark).
