"""Create Shroom-only configuration and GAS assets; roster integration is separate."""
from pathlib import Path
import unreal as u
prefix=(Path(u.Paths.project_dir())/'Scripts/GA/author_demon_gameplay.py').read_text().split('attacks=[]')[0]
prefix=prefix.replace('MonsterWave1','ShroomDesign').replace('/Demon/Expansion','/Shroom/Expansion').replace('DemonGameplayV1','ShroomGameplayV1')
exec(compile(prefix,'shroom_asset_helpers','exec'),globals())
attacks=[]
fxpath=R+'/NS_Shroom_Spores';fx=u.load_asset(fxpath) if u.EditorAssetLibrary.does_asset_exist(fxpath) else None
if fx:assert u.EditorAssetLibrary.get_metadata_tag(fx,'AuthoringOwner')==owner
else:
 fx=u.EditorAssetLibrary.duplicate_asset('/Game/Free_Spells/VFX_Niagara/NS_Free_Spells_Aura_Soul',fxpath)
 assert fx;u.EditorAssetLibrary.set_metadata_tag(fx,'AuthoringOwner',owner)
save(fx)
for name,cls,config_class,values in [
 ('Slam',u.ShroomSlamAbility,u.StoneGolemAttackConfig,dict(radius=120.,activation_range=170.,damage_multiplier=1.,cooldown=3.,animation_delay=.35,lock_time=.2,contact_time=16/30,contact_tolerance=.06,recovery_end=1.1,selection_weight=3.)),
 ('Spore',u.ShroomSporeAbility,u.ShroomSporeConfig,dict(radius=180.,activation_range=220.,damage_multiplier=.5,cooldown=9.,animation_delay=.45,lock_time=.3,contact_time=.8,contact_tolerance=.06,recovery_end=1.85,selection_weight=1.))]:
 config=data('DA_Shroom_'+name,config_class);t=u.StoneGolemAttackTuning()
 for k,v in values.items():t.set_editor_property(k,v)
 for k,v in {'shape':u.StoneGolemShape.CIRCLE,'center_offset':u.Vector(),'head_offset':u.Vector(0,0,60),'exclamation':name=='Spore','require_line_of_sight':True,'impact_socket':'Root','montage':u.load_asset(R+'/Animations/AM_Shroom_'+name),'warning_material':u.load_asset('/Game/BluePrints/Characters/StoneGolem/M_SG_Warning'),'impact_effect':fx if name=='Spore' else u.load_asset('/Game/Assets/Effects/Combat/NS_BloodImpact_green'),'impact_scale':.4 if name=='Spore' else 1.5,'impact_lifetime':3.1 if name=='Spore' else .7}.items():t.set_editor_property(k,v)
 config.set_editor_property('tuning',t)
 if name=='Spore':
  config.set_editor_property('duration',3.);config.set_editor_property('period',1.)
  tag=u.GameplayTag();tag.import_text('(TagName="Damage.Magic")');config.set_editor_property('damage_type',tag)
 save(config);ability,cdo=bp('GA_Shroom_'+name,cls.static_class());cdo.set_editor_property('attack_config',config)
 u.BlueprintEditorLibrary.compile_blueprint(ability);save(ability);attacks.append(ability.generated_class())
source=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Demon/Expansion/BP_DemonWarrior'))
config=data('DA_Shroom',u.MonsterCombatConfig)
for k,v in {'mesh':u.load_asset('/Game/Assets/Enemies/Shroom/Mesh/SKM_Shroom'),'anim_class':u.EditorAssetLibrary.load_blueprint_class(R+'/Animations/ABP_Shroom_Enemy'),'behavior':u.load_asset('/Game/BluePrints/Characters/Demon/Expansion/BT_DemonWarrior'),'base_damage':20.,'walk_speed':180.,'attacks':attacks,'damage_effect':u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage')}.items():
 assert v is not None;config.set_editor_property(k,v)
save(config)
actor,cdo=bp('BP_Shroom',u.TelegraphedEnemyCharacter.static_class());cdo.set_editor_property('combat_config',config)
for k in ['character_class','ai_controller_class']:cdo.set_editor_property(k,source.get_editor_property(k))
cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
mesh=cdo.get_component_by_class(u.SkeletalMeshComponent);mesh.set_editor_property('relative_location',u.Vector(0,0,-55));mesh.set_editor_property('relative_rotation',u.Rotator(yaw=-90))
cdo.get_component_by_class(u.CapsuleComponent).set_capsule_size(45,55)
bar=cdo.get_editor_property('health_bar');bar.set_editor_property('widget_class',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/UI/ProgressBar/WBP_EnemyHealthBar'));bar.set_editor_property('space',u.WidgetSpace.SCREEN);bar.set_editor_property('draw_at_desired_size',True);bar.set_editor_property('relative_location',u.Vector(0,0,85))
u.BlueprintEditorLibrary.compile_blueprint(actor);save(actor)
(run.parent/'gameplay-assets.json').write_text(json.dumps({'saved':saved,'backup':str(run),'integrated':False},indent=2))
