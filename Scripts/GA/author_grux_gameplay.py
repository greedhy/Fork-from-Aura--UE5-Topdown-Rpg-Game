"""Owned Grux assets. Does not change the dungeon BossClass."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir()).resolve();run=root/'Saved/GAAuthoring/GruxDesign'/uuid.uuid4().hex;run.mkdir(parents=True)
R='/Game/BluePrints/Characters/Grux/Expansion';owner='GruxGameplayV1'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};saved=[]
def asset(name,cls,factory):
 path=R+'/'+name;assert path not in dirty,'Unsaved '+path
 if u.EditorAssetLibrary.does_asset_exist(path):
  a=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')==owner
  shutil.copy2(root/'Content'/(path.removeprefix('/Game/')+'.uasset'),run/(name+'.uasset'))
 else:a=u.AssetToolsHelpers.get_asset_tools().create_asset(name,R,cls,factory)
 assert a;u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner',owner);return a
def data(name,cls):
 f=u.DataAssetFactory();f.set_editor_property('data_asset_class',cls);return asset(name,cls,f)
def bp(name,cls):
 f=u.BlueprintFactory();f.set_editor_property('parent_class',cls);a=asset(name,u.Blueprint,f)
 u.BlueprintEditorLibrary.compile_blueprint(a);return a,u.get_default_object(a.generated_class())
def save(a):
 assert u.EditorAssetLibrary.save_loaded_asset(a,False);saved.append(a.get_path_name())
def tuning(clip,**values):
 t=u.StoneGolemAttackTuning()
 defaults=dict(shape=u.StoneGolemShape.SECTOR,radius=240.,angle=110.,activation_range=280.,animation_delay=.35,lock_time=.25,contact_time=.25,contact_tolerance=.06,recovery_end=1.5,damage_multiplier=1.,cooldown=4.5,selection_weight=1.,center_offset=u.Vector(),head_offset=u.Vector(0,0,110),impact_socket='weapon_r',impact_scale=.8,impact_lifetime=.6,require_line_of_sight=True)
 defaults.update(values)
 for k,v in defaults.items():t.set_editor_property(k,v)
 t.set_editor_property('montage',u.load_asset(R+'/Animations/AM_Grux_'+clip))
 t.set_editor_property('warning_material',u.load_asset('/Game/BluePrints/Characters/StoneGolem/M_SG_Warning'))
 t.set_editor_property('impact_effect',u.load_asset('/Game/Assets/Effects/Combat/NS_CombatImpact'))
 return t
attacks=[]
for name,cls,kind,first,followup in [
 ('Combo',u.GruxComboAbility,u.GruxAttackKind.COMBO,tuning('Left',damage_multiplier=.8,selection_weight=3.,impact_socket='weapon_l'),tuning('Right',animation_delay=.3,lock_time=.2)),
 ('Charge',u.GruxChargeAbility,u.GruxAttackKind.CHARGE,tuning('Charge',shape=u.StoneGolemShape.RECTANGLE,length=600.,width=240.,radius=600.,activation_range=850.,animation_delay=.6,lock_time=.4,contact_time=.05,contact_tolerance=.04,recovery_end=1.35,damage_multiplier=.5,cooldown=10.),tuning('Uppercut',radius=200.,angle=90.,animation_delay=.3,lock_time=.2,contact_time=.3,recovery_end=1.9,damage_multiplier=1.1,knockback_speed=200.,knockback_up_speed=350.)),
 ('Roar',u.GruxRoarAbility,u.GruxAttackKind.ROAR,tuning('Roar',radius=250.,activation_range=800.,animation_delay=.4,lock_time=.25,contact_time=.3,recovery_end=1.85,damage_multiplier=0.,cooldown=12.,draw_footprint=False),None)]:
 config=data('DA_Grux_'+name,u.GruxAttackConfig);config.set_editor_property('kind',kind)
 if name=='Roar':
  first.set_editor_property('impact_effect',u.load_asset('/Game/Assets/Effects/Combat/NS_GroundSummon'))
  first.set_editor_property('impact_lifetime',1.2);first.set_editor_property('impact_scale',1.2)
  config.set_editor_property('roar_armor',25.);config.set_editor_property('roar_duration',6.)
 config.set_editor_property('tuning',first)
 if followup:config.set_editor_property('followup',followup)
 config.set_editor_property('charge_duration',.5);save(config)
 ability,cdo=bp('GA_Grux_'+name,cls.static_class());cdo.set_editor_property('attack_config',config)
 u.BlueprintEditorLibrary.compile_blueprint(ability);save(ability);attacks.append(ability.generated_class())
source=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Demon/Expansion/BP_DemonWarrior'))
config=data('DA_GruxBoss',u.MonsterCombatConfig)
for k,v in {'mesh':u.load_asset('/Game/ParagonGrux/Characters/Heroes/Grux/Meshes/Grux'),'anim_class':u.EditorAssetLibrary.load_blueprint_class(R+'/Animations/ABP_Grux_Enemy'),'behavior':u.load_asset('/Game/BluePrints/AI/BehaviorTree/BT_EnemyBehaviorTree'),'base_damage':45.,'walk_speed':320.,'attacks':attacks,'damage_effect':u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage')}.items():
 assert v is not None,k;config.set_editor_property(k,v)
save(config)
actor,cdo=bp('BP_GruxBoss',u.GruxEnemyCharacter.static_class());cdo.set_editor_property('combat_config',config)
cdo.set_editor_property('level',3)
for k in ['character_class','ai_controller_class']:cdo.set_editor_property(k,source.get_editor_property(k))
cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
mesh=cdo.get_component_by_class(u.SkeletalMeshComponent)
mesh.set_editor_property('relative_location',u.Vector(0,0,-130));mesh.set_editor_property('relative_rotation',u.Rotator(yaw=-90));mesh.set_editor_property('relative_scale3d',u.Vector(1,1,1))
cdo.get_component_by_class(u.CapsuleComponent).set_capsule_size(55.,130.)
bar=cdo.get_editor_property('health_bar');bar.set_editor_property('widget_class',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/UI/ProgressBar/WBP_EnemyHealthBar'))
bar.set_editor_property('space',u.WidgetSpace.SCREEN);bar.set_editor_property('draw_at_desired_size',True);bar.set_editor_property('relative_location',u.Vector(0,0,145))
u.BlueprintEditorLibrary.compile_blueprint(actor);save(actor)
(run.parent/'gameplay-assets.json').write_text(json.dumps({'saved':saved,'backup':str(run),'integrated':False,'status':'runtime_validation_pending'},indent=2))


