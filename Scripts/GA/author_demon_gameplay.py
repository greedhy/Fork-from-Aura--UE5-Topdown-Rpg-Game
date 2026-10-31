"""Author owned Demon GAS assets; balance/timing remain subject to runtime acceptance."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir()).resolve();run=root/'Saved/GAAuthoring/MonsterWave1'/uuid.uuid4().hex;run.mkdir(parents=True)
R='/Game/BluePrints/Characters/Demon/Expansion';owner='DemonGameplayV1'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
tools=u.AssetToolsHelpers.get_asset_tools();saved=[]
def asset(name,cls,factory):
 path=R+'/'+name;assert path not in dirty,'Unsaved '+path
 if u.EditorAssetLibrary.does_asset_exist(path):
  a=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')==owner
  file=root/'Content'/(path.removeprefix('/Game/')+'.uasset');shutil.copy2(file,run/file.name)
 else:a=tools.create_asset(name,R,cls,factory);assert a
 u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner',owner);return a
def data(name,cls):
 f=u.DataAssetFactory();f.set_editor_property('data_asset_class',cls);return asset(name,cls,f)
def bp(name,cls):
 f=u.BlueprintFactory();f.set_editor_property('parent_class',cls);a=asset(name,u.Blueprint,f)
 u.BlueprintEditorLibrary.compile_blueprint(a);return a,u.get_default_object(a.generated_class())
def save(a):
 assert u.EditorAssetLibrary.save_loaded_asset(a,False);saved.append(a.get_path_name())
attacks=[]
for name,cls,clip,values in [
 # Native Claw identity is retained for compatibility; the approved attack is now TailStab.
 ('TailStab',u.DemonClawAbility,'ClawL',dict(radius=100.,activation_range=110.,angle=80.,damage_multiplier=1.,cooldown=1.8,animation_delay=.3,lock_time=.2,contact_time=.4,contact_tolerance=.06,recovery_end=1.4,selection_weight=3.,single_target=True,draw_footprint=False)),
 ('Tailspin',u.DemonTailspinAbility,'Tailspin',dict(radius=100.,activation_range=110.,angle=160.,damage_multiplier=1.25,cooldown=6.,animation_delay=.45,lock_time=.3,contact_time=.4166667,contact_tolerance=.06,recovery_end=1.55,selection_weight=1.,single_target=False,draw_footprint=True))]:
 config=data('DA_Demon_'+name,u.StoneGolemAttackConfig)
 tuning=u.StoneGolemAttackTuning()
 for key,value in values.items():tuning.set_editor_property(key,value)
 tuning.set_editor_property('shape',u.StoneGolemShape.SECTOR)
 tuning.set_editor_property('center_offset',u.Vector())
 tuning.set_editor_property('head_offset',u.Vector(0,0,70))
 tuning.set_editor_property('montage',u.load_asset(R+'/Animations/AM_Demon_'+clip))
 tuning.set_editor_property('warning_material',u.load_asset('/Game/BluePrints/Characters/StoneGolem/M_SG_Warning'))
 tuning.set_editor_property('impact_socket','TailSocket')
 tuning.set_editor_property('impact_effect',u.load_asset('/Game/Assets/Effects/Combat/NS_CombatImpact'))
 tuning.set_editor_property('impact_scale',.3)
 tuning.set_editor_property('impact_lifetime',.6)
 config.set_editor_property('tuning',tuning);save(config)
 ability,cdo=bp('GA_Demon_'+name,cls.static_class());cdo.set_editor_property('attack_config',config)
 u.BlueprintEditorLibrary.compile_blueprint(ability);save(ability);attacks.append(ability.generated_class())
source=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Demon/BP_Demon_Warrior'))
source_mesh=source.get_component_by_class(u.SkeletalMeshComponent)
config=data('DA_DemonWarrior',u.MonsterCombatConfig)
for key,value in {'mesh':source_mesh.get_editor_property('skeletal_mesh_asset'),'anim_class':source_mesh.get_editor_property('anim_class'),
 'behavior':u.load_asset(R+'/BT_DemonWarrior'),'base_damage':25.,'walk_speed':250.,'attacks':attacks,
 'damage_effect':u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage')}.items():
 assert value is not None,key;config.set_editor_property(key,value)
save(config)
actor,cdo=bp('BP_DemonWarrior',u.TelegraphedEnemyCharacter.static_class())
cdo.set_editor_property('combat_config',config)
cdo.set_editor_property('character_class',source.get_editor_property('character_class'))
cdo.set_editor_property('ai_controller_class',source.get_editor_property('ai_controller_class'))
cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
mesh=cdo.get_component_by_class(u.SkeletalMeshComponent)
for key in ['relative_location','relative_rotation','relative_scale3d']:
 mesh.set_editor_property(key,source_mesh.get_editor_property(key))
capsule=cdo.get_component_by_class(u.CapsuleComponent);old=source.get_component_by_class(u.CapsuleComponent)
capsule.set_capsule_size(old.get_unscaled_capsule_radius(),old.get_unscaled_capsule_half_height())
bar=cdo.get_editor_property('health_bar')
bar.set_editor_property('widget_class',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/UI/ProgressBar/WBP_EnemyHealthBar'))
bar.set_editor_property('space',u.WidgetSpace.SCREEN);bar.set_editor_property('draw_at_desired_size',True);bar.set_editor_property('relative_location',u.Vector(0,0,110))
u.BlueprintEditorLibrary.compile_blueprint(actor);save(actor)
(run.parent/'demon-gameplay-assets.json').write_text(json.dumps({'saved':saved,'backup':str(run),'integrated':False,'timing_status':'candidate_requires_visual_acceptance'},indent=2))
