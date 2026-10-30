# StoneGolem Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task.

**Goal:** Deliver the approved stationary StoneGolem elite attacks through traditional GAS, with asset tuning, warnings and pool-safe cleanup.
**Architecture:** Dedicated animation/config assets; reuse EnemyCharacter, ASC, damage and AI. One shared attack lifecycle with three thin GA variants.
**Tech Stack:** UE 5.8, C++, GAS, Unreal Python, SOMOLMCP.
**Spec:** [StoneGolem design](../../stone-golem-elite-design.md), [monster standard](../../monster-development-standard.md).

## Global constraints

- Preserve imported source animations and unrelated working changes; no automatic commit.
- HeavyHammer/Quake share one isolated slam; ShieldBash uses only the shield segment.
- Elite remains outside ordinary enemy pool eligibility; lifecycle must support reuse.
- Animation validation precedes damage integration; automation precedes user PIE acceptance.

## Review focus

- Crop must retain the requested keys, not merely the requested duration.
- Root lock must prevent visual drift from collision and warning geometry.
- Death during damage callback must invalidate attack immediately without unsafe GAS reentry.
- Old callbacks must not affect a new attack or new actor lease.
- Warning and damage boundaries must share frozen parameters, including floor and occlusion.

## Tasks and evidence ledger

- [ ] Animation gate: `Scripts/GA/StoneGolem/author_animations.py` and `verify_animations.py`; create dedicated Slam/ShieldBash sequences in `/Game/BluePrints/Characters/StoneGolem/Animations`. Assert exact source-to-derived bone correspondence, root identity, duration, and contact time. Visually check entry, contact, exit with attachments.
- [ ] Config and lifecycle: typed DataAssets and shared traditional GA; validate finite shape/timing, one commit, server damage, cancel/death/lease cleanup, genuine cooldown and distinct attack identity.
- [ ] Enemy integration: minimal startup grant hook shared with wake; dedicated monster config, existing chase/target selection, montage playback and immediate death invalidation.
- [ ] Presentation: red footprint and exclamation lifecycle; inspect and configure actual Free_Spells effects; animation/impact/location match.
- [ ] Automated cases: config failures, boundaries, wall/floor, cancellation, cooldown, duplicate event, two lifetimes, stale callbacks; editor asset readback.
- [ ] PIE handoff: dedicated reproducible test entry, per-GA checks, evidence and unresolved limits. User supplies acceptance.

### Rulings

- Work in current UE project because required monster imports and pool implementation are uncommitted here, and MCP is bound to this project. Isolate new assets/scripts by StoneGolem directory; do not create a checkout missing those dependencies.
- Native crop adapter only checks length and uses removal semantics. Two-step removal also failed source-pose comparison in this environment. Explicitly write sampled source local bone keys and shifted float curves, then compare every retained frame and half-frame.
- User confirmed animation adaptation and exclusive editor use in this turn. No repeated approval for those steps.

### Current status

Animation assets saved: AS_SG_Slam, AS_SG_ShieldBash, AM_SG_Slam, AM_SG_ShieldBash. Data gate passes: raw/curve/compressed pose checks, root identity, timing, source hash preservation. Montage readback confirms single valid tracks and 0.15s blend. Actual contact/dynamic blending and AnimBP Slot remain open; no new GA or enemy gameplay integration yet.

Reviewer findings on curves, report naming and setting assertions addressed. Author reruns reject unowned and dirty targets, verify source identity, back up dedicated sequences, and record partial save progress. Native montage tool generated empty assets; replaced only those newly generated assets via AnimMontageFactory and independently read back correct lengths/slots.

### AnimBP continuation

- Created dedicated `ABP_SG_Elite` from the source AnimBP; removed its missing ControlRig node and connected DefaultSlot directly to output. Native graph readback verifies the link; compile reports BS_UpToDate.
- Source event graph uses a generic Character cast, so its movement update can be retained. Actual sequence references still point to StoneGolem demo MM_* assets; dedicated StoneGolem idle/walk/jog and BlendSpace conversion is pending.
- UE entered PIE during this phase and rejected the locomotion asset duplication. No locomotion assets were successfully authored by that failed script. User has been asked to end PIE; do not stop their session or mutate assets until they reply.
- Prepared `setup_animation_probe.py` and `run_animation_probe.py` for an isolated unsaved test world. Not executed yet. They are intended to measure real montage progress, planned-window sampling, actor drift and playback end; real contact remains a separate visual check.

### Runtime continuation and contact blocker

- User ended PIE. Dedicated Idle/Walk/Jog and BS_SG_Locomotion saved; speed axis 0–300, samples 0/150/300. AnimGraph now Locomotion → DefaultSlot → Output, compiled and saved.
- Isolated transient-world playback passed for both montages (run `f1315a5e53e64a55a861e70ca35432c0`): progress, planned-window samples, zero actor drift, playback end; maximum contact-window socket pose error 0.0173/0.0309 cm. Initial no-floor probe fell because Character startup resets movement mode; runtime setup now explicitly disables movement/gravity before sampling.
- New actual LOD0 vertex test found **27.8364 cm** hammer-to-floor gap at derived frame 21/0.7 s (4433 vertices). Old 6.7 cm result used transformed AABB corners and is not actual surface contact. Animation gate remains incomplete; do not integrate damage against an uncorrected contact pose.
- Asked user whether to preserve literal ground contact with dedicated upper-body/arm pose correction (recommended), or change the attack to a remote ground shock. This is a material presentation choice beyond the approved crop/root-lock adaptation.
- Runtime editor screenshots captured the editor world, not PIE; they are not runtime visual evidence. `static-contact-with-floor.png` is refreshed static single-node pose evidence only. Runtime evidence is the sampled AnimInstance/socket report. Original map restored via `restore_animation_probe.py`.

### Approved contact correction

- User approved preserving literal ground contact with dedicated pose correction. Authored AS_SG_Slam_Contact and AM_SG_Slam_Contact; preserve original crop and imported assets.
- Only spine_01/upperarm_r rotations change, with smooth envelope frames8–32, peak21; no local translation or scale changes. Original clip boundary and lower-body world transforms are invariant.
- Independent 120Hz geometry: planned .7s hammer surface gap1.50cm, minimum1.46cm at .7083s; no penetration. Runtime actual attached mesh transform gap1.4996cm; playback/pose/zero actor drift/end pass. Side static visual evidence saved as corrected-contact-side.png.
- Review findings addressed: gate binds planned impact time and penetration tolerance; reject duplicate probe and restore prior dilation; reject dirty source, validate source range/fps, and verify complete variant invariants before save. Scope remains isolated animation, not full GA/pool/game acceptance.
- Next integration must reference AM_SG_Slam_Contact for HeavyHammer/Quake and AM_SG_ShieldBash for shield, preserving approved timing. Actual target contact, game camera readability, and blends remain part of user PIE acceptance.


### Gameplay implementation and regression (current)

See [implementation and acceptance](../../stone-golem-implementation-and-acceptance.md). Dedicated native shared GAS lifecycle, three configured GA assets, frozen projected warning geometry, owned Free_Spells FX, pool generation invalidation and elite profile integration are implemented. Editor target build passed. ReviewRegression: 10/10 native tests passed. Real PIE: three damage cases and seven FX/interruption/death cases passed; AI tag selector and speed-driven locomotion passed. Final user visual/game acceptance and multiplayer remain unverified. Earlier ledger entries above are historical, not current blockers.
