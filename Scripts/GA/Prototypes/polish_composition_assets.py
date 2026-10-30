"""Isolated traditional GAS presentation variants; preserve all gameplay tuning."""
import unreal as u
import json, shutil, uuid
from pathlib import Path

root=Path(u.Paths.project_dir()).resolve()
run=root/'Saved/GAAuthoring/CompositionPolish'/uuid.uuid4().hex
run.mkdir(parents=True)
base='/Game/BluePrints/AbilitySystem/Player/Ability/Compositions'
art='/Game/Art/CompositionEffects'
report={'run_id':run.name,'success':False,'changes':[],'effects':[]}
def save(a):
    assert u.EditorAssetLibrary.save_loaded_asset(a,False),a.get_path_name()
def fx(name,source):
    path=art+'/NS_'+name
    a=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
    assert isinstance(a,u.NiagaraSystem),path
    save(a); report['effects'].append(path)
    return a
def edit(name,**values):
    path=base+'/DA_'+name
    a=u.load_asset(path); assert a and a.is_valid_configuration(),path
    src=root/'Content'/(path.removeprefix('/Game/')+'.uasset')
    dest=run/'backup'/src.relative_to(root); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest)
    before={k:str(a.get_editor_property(k)) for k in values}
    for k,v in values.items(): a.set_editor_property(k,v)
    assert a.is_valid_configuration(),path
    save(a)
    for k,v in values.items():
        actual=a.get_editor_property(k)
        assert (str(actual)==str(v) if k in ('summary','display_name') else actual==v),(path,k)
    report['changes'].append({'asset':path,'before':before,'after':{k:str(a.get_editor_property(k)) for k in values}})
try:
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'Save pending edits before authoring'
    fire=fx('FireSeed_Field','/Game/Free_Spells/VFX_Niagara/NS_Free_Spells_Aura_Fire')
    frost=fx('FrostFan_Projectile','/Game/Art/TerrainSurfaces/Effects/NS_Frost_Status')
    frost_hit=fx('Frost_Impact','/Game/Assets/Effects/Shock/NS_Sparks')
    # Use the established frost sprite material on the isolated one-shot impact.
    material=u.load_asset('/Game/Art/TerrainSurfaces/Effects/MI_Frost_Status')
    changed=0
    for obj in u.ObjectIterator(u.NiagaraSpriteRendererProperties):
        if obj.get_path_name().startswith(frost_hit.get_path_name()+':'):
            obj.set_editor_property('material',material); changed+=1
    assert changed>0,'No frost impact sprite renderer found'
    save(frost_hit)
    vines=fx('Bramble_Warning','/Game/Art/TerrainSurfaces/Effects/NS_Vines_Surface')
    thunder=fx('StormSeal_Field','/Game/Free_Spells/VFX_Niagara/NS_Free_Spells_Aura_Lightning')
    sparks=fx('StormSeal_Pulse','/Game/Assets/Effects/Shock/NS_Sparks')
    blast=fx('StormSeal_Blast','/Game/Free_Spells/VFX_Niagara/NS_Free_Spells_Explosion')
    ring=fx('Aftershock_Ring','/Game/Assets/Effects/Stun/NS_Halo')
    ripple=fx('Ripple_Ring','/Game/Assets/Effects/Stun/NS_Halo')
    hunter=fx('HunterSentry_Core','/Game/Free_Spells/VFX_Niagara/NS_Free_Spells_Aura_Soul')
    edit('FireSeed',summary='Fire projectile. Each enemy hit creates a stationary fire patch; child nodes do not charge mana.')
    edit('FireSeed_Field',loop_vfx=fire,ground_presentation=True,loop_vfx_scale=u.Vector(1.8,1.8,1),impact_vfx=None,summary='Fire patch: first pulse after one period; final scheduled pulse occurs before expiry.')
    edit('FrostFan',loop_vfx=frost,impact_vfx=frost_hit,loop_vfx_scale=u.Vector(.35,.35,.35),impact_vfx_scale=u.Vector(.5,.5,.5),summary='Fan of frost projectiles. Each enemy hit leaves a separate frost surface; damage type is unchanged.')
    edit('FrostFan_Ground',summary='Enemy-only frost surface at the projected hit position; its lifetime comes from Duration.')
    edit('BrambleMine',loop_vfx=vines,loop_vfx_scale=u.Vector(2.2,2.2,1),ground_presentation=True,impact_vfx=None,summary='Arms, triggers on nearby enemies, then bursts and leaves vines. Natural expiry also triggers the child burst.')
    edit('BrambleMine_Burst',display_name=u.Text('Bramble Burst'),ground_presentation=True,impact_vfx_scale=u.Vector(.73,.73,.73),summary='One burst at the trap origin; vines appear when this short burst node expires.')
    edit('BrambleMine_Ground',summary='Enemy-only vines at the trap origin. Ends with this node lifetime.')
    edit('StormSeal',loop_vfx=thunder,impact_vfx=sparks,ground_presentation=True,loop_vfx_scale=u.Vector(2.5,2.5,1),summary='Lightning field; periodic pulses include the final boundary, followed by the terminal burst.')
    edit('StormSeal_Burst',display_name=u.Text('Storm Burst'),impact_vfx=blast,ground_presentation=True,impact_vfx_scale=u.Vector(.83,.83,.83),summary='One terminal blast at the field origin.')
    edit('Aftershock',loop_vfx=ring,ground_presentation=True,loop_vfx_scale=u.Vector(4.2,4.2,.25),summary='Warning at the initial caster position. After the delay, a ring strikes and each enemy hit produces a small burst.')
    edit('Aftershock_Ring',loop_vfx=ring,ground_presentation=True,summary='Single annulus hit; inner area is safe. Secondary bursts are centred on hit enemies.')
    edit('Aftershock_Burst',impact_vfx_scale=u.Vector(.3,.3,.3),summary='Small secondary explosion centred on an enemy hit by the ring.')
    edit('FrostFault',impact_vfx=frost_hit,impact_vfx_scale=u.Vector(1,1,1),summary='Instant forward rectangle. Each enemy actually hit leaves frost ground; aiming distance does not change line length.')
    edit('FrostFault_Ground',summary='Enemy-only frost surface under an actual line hit; expires with this node.')
    edit('RippleMine',loop_vfx=ripple,loop_vfx_scale=u.Vector(2.2,2.2,.25),ground_presentation=True,impact_vfx=None,summary='Armed trap. Trigger or natural expiry starts a short fuse, then an outward wave; no instant explosion damage.')
    edit('RippleMine_Delay',loop_vfx=ripple,loop_vfx_scale=u.Vector(2.2,2.2,.25),ground_presentation=True,summary='Fuse remains at the trap origin; wave starts only after ArmDelay.')
    edit('RippleMine_Wave',loop_vfx=ripple,ground_presentation=True,summary='Expanding front damages each enemy once; enemies behind a passed front are not hit again.')
    edit('HunterSentry',loop_vfx=hunter,ground_presentation=True,summary='Stationary sentry at cast position. Acquires enemies periodically; ends at shot cap or lifetime.')
    edit('HunterSentry_Shot',impact_vfx=None,summary='Homing shot. Successful enemy hit spawns the separate Hunter Blast; no duplicate projectile explosion.')
    edit('HunterSentry_Burst',impact_vfx_scale=u.Vector(.333,.333,.333),summary='Single secondary burst at the homing hit enemy.')
    report['success']=True
finally:
    (run/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (run.parent/'latest-authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
