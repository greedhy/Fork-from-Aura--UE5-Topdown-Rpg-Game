# Traditional GAS composition polish

Goal: validate and polish FireSeed, FrostFan, BrambleMine, StormSeal, Aftershock, FrostFault, RippleMine and HunterSentry, then hand off for human PIE acceptance.

Architecture: retain UPrototypeAbility / UAbilityPrototype / APrototypeRuntime and existing composition graphs. PureMass assets are excluded. Preserve balancing and existing grants; fix demonstrated scheduling defects and isolate presentation assets.

Tech stack: UE 5.8.1, GAS, Niagara, Unreal Python, native automation.

- [x] Export actual eight GA definitions and all reachable nodes. Baseline: Saved/GAAuthoring/CompositionPolish/27880da0ef1048f7b34d592528bc9b10/audit.json.
- [x] Run existing 27 prototype automation tests in editor; all succeeded on 2026-10-29 at 07:40 UTC.
- [x] Add real saved-asset Field final-boundary/catchup regression. Red report: Saved/GAAuthoring/CompositionPolish/Red/index.json. Both fields incorrectly dealt zero damage in a single lifetime-sized frame.
- [x] Fix Field scheduler; run new test and all prototype regression tests. GreenBaseline/index.json: 28 Success, zero failed/not-run; 27 tests have fixture skeletal-mesh warnings.
- [ ] Add configurable presentation transform, ground alignment and size matching without changing unrelated defaults.
- [x] Create independent composition Niagara variants and update only composition nodes; snapshot assets before writes; read back independently.
- [x] Correct stale summary text and retain quantitative root descriptions.
- [ ] Verify Niagara compilation, asset graph validity, timing, cancellation and real GA activation.
- [x] Deliver per-skill PIE steps and keep human visual acceptance pending.

Final status: editor ownership resolved; final build succeeded. Twenty composition assets updated with backups; eight GA graphs independently read back; ten Niagara variants ready with zero compile errors; 28 final automation tests Success. Human PIE rendering/size/timing acceptance remains pending. Evidence: Saved/GAAuthoring/CompositionPolish/delivery-check.json.

## Behavior and presentation contract (current level-one configuration)

| GA | Behavior | Presentation placement and timing |
|---|---|---|
| FireSeed | 20 hit; field radius 180, 8 each second for 4s | Fire projectile; hit burst at collision; ground fire under hit enemy for field lifetime |
| FrostFan | 3 projectiles over 45 degrees, 12 each; frost surface 300 x 300 for 4s | Frost projectiles; frost impact; ground projected separately for each actual hit |
| BrambleMine | arms .75s; radius 220; trigger 10; child burst 25; vines 440 x 440 for 4s after .4s burst | Ground trap, single child explosion, then vines at same ground position; untriggered expiry at 6s also produces child by current OnExpire contract |
| StormSeal | radius 250; 10 each second for 3s, then 30 burst | Lightning field at selected position, pulse at 1/2/3s, terminal blast after last pulse |
| Aftershock | fixed initial caster position; delay 1s; ring 100–420 deals 24; each hit produces radius-90 burst for 12 | Warning at fixed origin, ring boundaries at detonation; secondary bursts on hit enemies, not caster |
| FrostFault | forward line 650 x 140, 22 per enemy; each hit frost surface 260 x 260 for 3s | Ground-aligned line in aim direction; frost appears only at actual hit enemies |
| RippleMine | arms .75s; trigger or 12s expiry; .6s fuse; expanding radius-450 wave, speed 400, damage 28 once per enemy | Ground trap, fuse warning at trap origin, expanding ring; no premature damaging explosion |
| HunterSentry | fixed caster-origin sentry; radius 700 acquisition, every 1s up to 3 shots within 5s; homing 18 plus radius-100 burst 10 | Stationary sentry indicator, projectiles from sentry towards chosen enemy, impact burst at enemy |

Damage types remain as configured; a frost visual does not silently introduce a new resistance type. Finite casts outlive the instant GA; caster death/context cancellation terminates runtime children. Trap natural expiry continues to emit OnExpire, matching current graph semantics.

## Review findings

## Free_Spells resource update

User authorized Free_Spells as a presentation source. Inventory found 18 Niagara systems. Six candidate systems were independently read through niagara_system_authoring_snapshot; evidence: Saved/GAAuthoring/CompositionPolish/free-spells-d9a6bb031a9444d3a71452c234e2d7b7.json.

Prepared source mapping: FireSeed_Field -> Aura_Fire; StormSeal -> Aura_Lightning, terminal blast -> Explosion; HunterSentry -> Aura_Soul. Circle and Shockwave remain candidates for warning/impact variants pending timing and size calibration, not automatically substituted for runtime-driven Ring/Wave.

The source systems expose user parameters, including Scale_All on Aura_Fire, and mix local-space and world-space emitters. Component scale alone must not be assumed to calibrate all emitters. Inspect parameter values and test rendered radius/duration before marking matching complete. Preserve Free_Spells source assets and tune independent CompositionEffects copies. Assignments have now been saved and independently read back. Actual rendered dimensions and timing still require PIE acceptance.

FrostFan uses the fire projectile and explosion. StormSeal uses summon/arcane effects. All warning rings use a generic halo; field and trap scales are not configured from gameplay radius. Several Summary values still describe their source prototypes. Menu composition formatting replaces rather than appends root details, hiding range/duration. These need correction and visual verification; presence of a Niagara reference alone is not acceptance.
