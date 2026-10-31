"""Three mutually exclusive, telegraphed Shaman GAS abilities with owned summon cleanup."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());backup=root/'Saved/GAAuthoring/MonsterWave1'/uuid.uuid4().hex;backup.mkdir()
R='/Game/BluePrints/Characters/Goblin/ShamanExpansion';owner='ShamanExpansionV1'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};saved=[]
def asset(name,cls,factory):
 path=R+'/'+name;assert path not in dirty
 if u.EditorAssetLibrary.does_asset_exist(path):
  a=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')==owner
  shutil.copy2(root/'Content'/(path.removeprefix('/Game/')+'.uasset'),backup/(name+'.uasset'))
 else:a=u.AssetToolsHelpers.get_asset_tools().create_asset(name,R,cls,factory)
 assert a;u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner',owner);return a
def data(name,cls):
 f=u.DataAssetFactory();f.set_editor_property('data_asset_class',cls);return asset(name,cls,f)
def bp(name,cls):
 f=u.BlueprintFactory();f.set_editor_property('parent_class',cls);a=asset(name,u.Blueprint,f)
 u.BlueprintEditorLibrary.compile_blueprint(a);return a,u.get_default_object(a.generated_class())
def save(a):
 assert u.EditorAssetLibrary.save_loaded_asset(a,False);saved.append(a.get_path_name())
attacks=[]
for name,cls,values in [
 ('Cast',u.ShamanCastAbility,dict(radius=650.,activation_range=650.,damage_multiplier=.8,cooldown=2.5,animation_delay=.25,lock_time=.15,contact_time=14/24,contact_tolerance=.06,recovery_end=2.,selection_weight=3.,single_target=True,draw_footprint=False,require_line_of_sight=True,impact_at_target=True)),
 ('Burst',u.ShamanBurstAbility,dict(radius=170.,activation_range=650.,damage_multiplier=1.2,cooldown=7.,animation_delay=.55,lock_time=.35,contact_time=9/24,contact_tolerance=.06,recovery_end=2.5,selection_weight=1.,single_target=False,draw_footprint=True,target_ground=True,require_line_of_sight=True)),
 ('Summon',u.ShamanSummonAbility,dict(radius=300.,activation_range=650.,damage_multiplier=0.,cooldown=12.,animation_delay=.5,lock_time=.3,contact_time=9/24,contact_tolerance=.06,recovery_end=2.4,selection_weight=1.,single_target=False,draw_footprint=False))]:
 config=data('DA_Sh_'+name,u.ShamanSummonConfig if name=='Summon' else u.StoneGolemAttackConfig)
 t=u.StoneGolemAttackTuning()
 for k,v in values.items():t.set_editor_property(k,v)
 t.set_editor_property('center_offset',u.Vector());t.set_editor_property('head_offset',u.Vector(0,0,100))
 t.set_editor_property('montage',u.load_asset(R+'/Animations/AM_Sh_'+name))
 t.set_editor_property('warning_material',u.load_asset('/Game/BluePrints/Characters/StoneGolem/M_SG_Warning'))
 fx={'Cast':'/Game/Assets/Effects/Combat/NS_CombatImpact','Burst':'/Game/Free_Spells/VFX_Niagara/NS_Free_Spells_Explosion','Summon':'/Game/Assets/Effects/Combat/NS_GroundSummon'}[name]
 if name=='Burst' and u.EditorAssetLibrary.does_asset_exist(R+'/Effects/NS_Sh_Burst'):fx=R+'/Effects/NS_Sh_Burst'
 t.set_editor_property('impact_effect',u.load_asset(fx));t.set_editor_property('impact_scale',.5 if name=='Burst' else .7)
 t.set_editor_property('impact_lifetime',1.5)
 config.set_editor_property('tuning',t)
 tag=u.GameplayTag();tag.import_text('(TagName="Damage.Magic")');config.set_editor_property('damage_type',tag)
 if name=='Summon':config.set_editor_property('minion_class',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Demon/Expansion/BP_DemonWarrior'))
 save(config)
 ability,cdo=bp('GA_Sh_'+name,cls.static_class());cdo.set_editor_property('attack_config',config)
 u.BlueprintEditorLibrary.compile_blueprint(ability);save(ability);attacks.append(ability.generated_class())
source=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Goblin/BP_Shaman'))
srcmesh=source.get_component_by_class(u.SkeletalMeshComponent)
config=data('DA_Shaman',u.MonsterCombatConfig)
for k,v in {'mesh':srcmesh.get_editor_property('skeletal_mesh_asset'),'anim_class':srcmesh.get_editor_property('anim_class'),'base_damage':25.,'walk_speed':200.,'attacks':attacks,'behavior':u.load_asset('/Game/BluePrints/AI/BehaviorTree/BT_EnemyBehaviorTree'),'damage_effect':u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage')}.items():
 assert v is not None,k;config.set_editor_property(k,v)
save(config)
actor,cdo=bp('BP_ShamanExpanded',u.ShamanEnemyCharacter.static_class());cdo.set_editor_property('combat_config',config)
for k in ['character_class','ai_controller_class']:cdo.set_editor_property(k,source.get_editor_property(k))
cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
mesh=cdo.get_component_by_class(u.SkeletalMeshComponent)
for k in ['relative_location','relative_rotation','relative_scale3d']:mesh.set_editor_property(k,srcmesh.get_editor_property(k))
caps=cdo.get_component_by_class(u.CapsuleComponent);old=source.get_component_by_class(u.CapsuleComponent)
caps.set_capsule_size(old.get_unscaled_capsule_radius(),old.get_unscaled_capsule_half_height())
weapon=cdo.get_editor_property('weapon');srcweapon=source.get_editor_property('weapon')
weapon.set_skeletal_mesh_asset(srcweapon.get_editor_property('skeletal_mesh_asset'))
for k in ['relative_location','relative_rotation','relative_scale3d']:weapon.set_editor_property(k,srcweapon.get_editor_property(k))
bar=cdo.get_editor_property('health_bar');bar.set_editor_property('widget_class',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/UI/ProgressBar/WBP_EnemyHealthBar'))
bar.set_editor_property('space',u.WidgetSpace.SCREEN);bar.set_editor_property('draw_at_desired_size',True);bar.set_editor_property('relative_location',u.Vector(0,0,110))
u.BlueprintEditorLibrary.compile_blueprint(actor);save(actor)
(root/'Saved/GAAuthoring/MonsterWave1/shaman-gameplay-assets.json').write_text(json.dumps({'saved':saved,'backup':str(backup),'integrated':False,'visual_timing':'candidate_source_notify_aligned'},indent=2))
