# Whole-floor lifetime and bounded enemy pool

User-approved scope: generate all rooms from the floor seed on entry; retain them until floor teardown. Pool common Actor/GAS enemies only. Add performance sampling; do not claim measured memory savings.

Implementation ledger:
- Existing floor assembly already retains all rooms and unloads them in EndPlay; preserve it.
- Task 1: verify pooled death, implement opt-in enemy sleep/reset and replicated presentation.
- Task 2: integrate a floor-owned bounded pool (default 12), overflow uses ordinary spawning. Only normal spawn requests opt in; never infer eligibility by BP class because normal and elite can share a class.
- Task 3: cumulative spawn/acquire/return timings and bounded periodic process-memory/frame samples, JSON export at teardown and callable report during play.
- Task 4: build, native lifecycle/capacity regressions, available real-BP integration verification, final review.

Ruling: retired actors become reusable only in a later encounter, not in another wave of the same encounter. This limits stale combat callbacks; capacity overflow remains an ordinary disposable actor. Cost: fewer reuse hits in a single fight.
Superseded by user steering: enemies keep their weapon attached and enter ragdoll while AI/actor logic sleeps. Pooled corpses simulate for NormalCorpseSeconds (default 1.5), then hide/stop physics and enter the idle pool. Reuse restores mesh attachment/transform/collision/animation. Pooled deaths still skip arbitrary Blueprint dissolve timelines; ordinary enemy death keeps existing dissolve/lifespan while retaining weapon attachment. Player death is unchanged.
Ruling: use the existing user workspace/feature branch; preserve unrelated staged assets, do not commit them.

Verification ledger:
- Initial pooled death regression failed as expected: visible actor and 5-second lifespan. Implemented explicit pooled lifecycle.
- Initial native suite: 36/36 passed (20 clean, 16 with existing/fixture warnings).
- Real BP solo, seed 42: pool-solo-01, 119 steps, complete floor Victory. 87 reuse hits; 15 pool misses; 3 overflow; total pool 12. This predates the user-requested ragdoll change.
- In that editor run, measured create mean/max 3.026/3.846 ms vs reuse 0.850/1.414 ms. Different classes and warm assets; not an A/B benchmark. Observed process peak 4,912,017,408 bytes includes editor, assets and all systems; not pool or floor allocation.
- Independent review identified same-asset Blackboard initialization preserving values. Initial fixture lacked AISystem and was falsely green; corrected fixture asserts initialization and initial target/distance. Corrected test failed with stale target and distance 777; implementation now clears all keys, including inherited keys.
- New corpse-visibility regression failed against the previous immediate-hide policy.
- Final native suite after ragdoll/blackboard changes: 38/38 passed (21 clean, 17 warnings), including RealBlueprintRagdollRestore (two leases), GAS reset, capacity/quarantine and performance report.
- Final real-BP multiplayer: pool-duo-ragdoll-02, 22 steps passed across two combat rooms, 10 pool hits. pool-duo-evidence.json verifies both server/client observed visible ragdolls, live reused leases, attached non-simulating weapons, and idle actors with physics/collision/actor+mesh ticks off. Eight checks passed.
- First multiplayer attempt stopped because Python cannot read the private lease property; added GetDungeonPoolLease() read-only Blueprint/MCP API and reran from a new PIE session.
- Export verified separate server/client files for the same run. Filename now includes world package, role and PID; prevents same-name PIE worlds overwriting each other.
- Not tested: packaged build, dedicated server, adverse latency, long-duration leak/VRAM attribution. External player effects sourced from pooled monsters retain their original ASC; cross-lease source-effect isolation is a future extension to validate when pooling enemies with long-lived outgoing effects.

Usage and performance collection:
- DA_DungeonGameplay inherits NormalPoolCapacity=12; set 0 for a fresh-run no-pool comparison. Capacity counts active, settling and idle actors. Overflow remains disposable. Pool fills lazily under existing per-frame spawn budgets; no up-front allocation of every encounter enemy.
- NormalCorpseSeconds=1.5 is clamped 0..10 at runtime. Corpse simulation is intentionally still active during that short interval; idle actors have physics, actor and component ticks disabled.
- PerformanceSampleInterval defaults to 1 second; at most 600 recent samples retained. Cumulative counters/timings remain for the whole run. Disable bSamplePerformance to disable periodic sampling/export.
- GetRunReport().performance exposes pool hits/misses/overflow, creation/reuse/reset/return timings and whole-process physical/virtual memory samples. DeltaSeconds is frame duration, not exclusive GameThread CPU time; GPU memory is not included.
- ExportPerformanceReport() writes Saved/RoguelikeGeneration/Performance/<run-id>-<world-package>-<role>-<pid>.json, also automatically on EndPlay. It records the pre-teardown state, not proof of memory reclamation.
- Rooms retain their existing whole-floor lifetime. Enemy pool ownership is the run director in that World, never GameInstance.

Startup investigation:
- An older PID 59844 started 16:11 and stopped logging during Concert loading after PoseSearch. Normal close failed; user authorized forced termination. Windows taskkill reported no running instance although tasklist/CIM still listed the PID. Root cause of that stale instance remains unproven.
- A fresh test editor loaded PoseSearch/Concert and L_RoguelikeRun in 16.74 seconds; dirty packages empty. Do not disable PoseSearch or delete caches without evidence.
- Standard DLL remained locked by the old process, so builds use UE ModuleWithSuffix and the generated module manifest. Successful tested builds and their module names are in Saved/RoguelikeGeneration/pool-*-build*.txt. Restarting Windows may be needed to clear a stuck OS process/handle; this is not automatically performed.

