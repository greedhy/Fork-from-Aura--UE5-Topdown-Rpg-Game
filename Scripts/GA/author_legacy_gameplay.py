"""Owned assets only; roster replacement follows runtime acceptance."""
from pathlib import Path
import unreal as u
prefix=(Path(u.Paths.project_dir())/'Scripts/GA/author_demon_gameplay.py').read_text().split('attacks=[]')[0]
prefix=prefix.replace('MonsterWave1','LegacyMonsterDesign').replace('/Demon/Expansion','/LegacyExpansion').replace('DemonGameplayV1','LegacyMonsterGameplayV1')
exec(compile(prefix,'legacy_helpers','exec'),globals())
projectile_path=R+'/BP_SlingRock';projectile=u.load_asset(projectile_path) if u.EditorAssetLibrary.does_asset_exist(projectile_path) else None
if projectile:assert u.EditorAssetLibrary.get_metadata_tag(projectile,'AuthoringOwner')==owner
else:
 projectile=u.EditorAssetLibrary.duplicate_asset('/Game/BluePrints/AbilitySystem/Enemy/Ability/BP_SlingShotRock',projectile_path)
 u.EditorAssetLibrary.set_metadata_tag(projectile,'AuthoringOwner',owner)
 u.BlueprintEditorLibrary.reparent_blueprint(projectile,u.EnemySlingProjectile.static_class())
u.BlueprintEditorLibrary.compile_blueprint(projectile)
u.get_default_object(projectile.generated_class()).get_component_by_class(u.ProjectileMovementComponent).set_editor_property('projectile_gravity_scale',0.)
u.get_default_object(projectile.generated_class()).get_component_by_class(u.ProjectileMovementComponent).set_editor_property('initial_velocity_in_local_space',False)
u.BlueprintEditorLibrary.compile_blueprint(projectile);assert str(projectile.get_editor_property('status'))!='BlueprintStatus.BS_ERROR';save(projectile)
attacks={}
for name,cls,rad,contact,delay,cd,end in [('Spear',u.GoblinSpearAbility,115.,.29,.3,1.8,1.55),('Sling',u.GoblinSlingAbility,650.,.175,.35,2.2,1.6),('GhoulL',u.GhoulLeftAbility,135.,.85,.25,2.5,2.35),('GhoulR',u.GhoulRightAbility,135.,.87,.25,2.5,2.35)]:
 cfg=data('DA_Attack_'+name,u.SlingAttackConfig if name=='Sling' else u.StoneGolemAttackConfig)
 t=u.StoneGolemAttackTuning()
 values={'shape':u.StoneGolemShape.SECTOR,'radius':rad,'angle':100. if name.startswith('Ghoul') else 70.,'activation_range':rad+10,'damage_multiplier':1.,'cooldown':cd,'animation_delay':delay,'lock_time':.2,'contact_time':contact,'contact_tolerance':.06,'recovery_end':end,'single_target':True,'draw_footprint':False,'warning_material':u.load_asset('/Game/BluePrints/Characters/StoneGolem/M_SG_Warning'),'require_line_of_sight':True,'center_offset':u.Vector(),'head_offset':u.Vector(0,0,80 if name.startswith('Ghoul') else 65),'montage':u.load_asset(R+'/Animations/AM_Legacy_'+name),'impact_at_target':True,'impact_effect':None if name=='Sling' else u.load_asset('/Game/Assets/Effects/Combat/NS_CombatImpact'),'impact_scale':.3,'impact_lifetime':.5}
 for k,v in values.items():t.set_editor_property(k,v)
 cfg.set_editor_property('tuning',t)
 if name=='Sling':
  for k,v in {'projectile_class':projectile.generated_class(),'speed':550.,'lifetime':2.,'muzzle_socket':'Hand-L'}.items():cfg.set_editor_property(k,v)
 save(cfg);ga,cdo=bp('GA_'+name,cls.static_class());cdo.set_editor_property('attack_config',cfg)
 u.BlueprintEditorLibrary.compile_blueprint(ga);save(ga);attacks[name]=ga.generated_class()
for name,src,abp,skills,damage,speed in [('GoblinSpear','Goblin/BP_GoblinSpear','Spear',['Spear'],20.,250.),('GoblinSlinger','Goblin/BP_Goblin_Slinshot','Sling',['Sling'],18.,220.),('Ghoul','Ghoul/BP_Ghoul','Ghoul',['GhoulL','GhoulR'],25.,250.)]:
 source=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/'+src));sm=source.get_component_by_class(u.SkeletalMeshComponent)
 cfg=data('DA_'+name,u.MonsterCombatConfig)
 for k,v in {'mesh':sm.get_editor_property('skeletal_mesh_asset'),'anim_class':u.EditorAssetLibrary.load_blueprint_class(R+'/Animations/ABP_Legacy_'+abp),'behavior':source.get_editor_property('behavior_tree') if name=='GoblinSlinger' else u.load_asset('/Game/BluePrints/Characters/Demon/Expansion/BT_DemonWarrior'),'base_damage':damage,'walk_speed':speed,'attacks':[attacks[x] for x in skills],'damage_effect':u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage')}.items():cfg.set_editor_property(k,v)
 save(cfg);actor,cdo=bp('BP_'+name,u.TelegraphedEnemyCharacter.static_class());cdo.set_editor_property('combat_config',cfg)
 for k in ['character_class','ai_controller_class']:cdo.set_editor_property(k,source.get_editor_property(k))
 cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
 m=cdo.get_component_by_class(u.SkeletalMeshComponent)
 for k in ['relative_location','relative_rotation','relative_scale3d']:m.set_editor_property(k,sm.get_editor_property(k))
 old=source.get_component_by_class(u.CapsuleComponent);cdo.get_component_by_class(u.CapsuleComponent).set_capsule_size(old.get_unscaled_capsule_radius(),old.get_unscaled_capsule_half_height())
 weapon=cdo.get_editor_property('weapon');oldweapon=source.get_editor_property('weapon')
 weapon.set_skeletal_mesh_asset(oldweapon.get_editor_property('skeletal_mesh_asset'))
 for k in ['relative_location','relative_rotation','relative_scale3d']:weapon.set_editor_property(k,oldweapon.get_editor_property(k))
 bar=cdo.get_editor_property('health_bar');bar.set_editor_property('widget_class',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/UI/ProgressBar/WBP_EnemyHealthBar'));bar.set_editor_property('space',u.WidgetSpace.SCREEN);bar.set_editor_property('draw_at_desired_size',True);bar.set_editor_property('relative_location',u.Vector(0,0,100))
 u.BlueprintEditorLibrary.compile_blueprint(actor);assert str(actor.get_editor_property('status'))!='BlueprintStatus.BS_ERROR';save(actor)
(run.parent/'gameplay-assets.json').write_text(json.dumps({'saved':saved,'backup':str(run),'integrated':False},indent=2))
