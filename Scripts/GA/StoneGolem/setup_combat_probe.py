"""An isolated unsaved arena with real GAS actors and no player save/load path."""
import unreal as u,json
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
project=Path(u.Paths.project_dir());out=project/'Saved/GAAuthoring/StoneGolemBuild'
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
loc,rot=u.EditorLevelLibrary.get_level_viewport_camera_info()
(out/'combat-probe-restore.json').write_text(json.dumps({'map':ed.get_editor_world().get_path_name().split('.')[0],'location':[loc.x,loc.y,loc.z],'rotation':[rot.pitch,rot.yaw,rot.roll]}))
R='/Game/BluePrints/Characters/StoneGolem'
path=R+'/BP_SG_TestGameMode'
if not u.EditorAssetLibrary.does_asset_exist(path):
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.MyGameModeBase.static_class())
    bp=u.AssetToolsHelpers.get_asset_tools().create_asset('BP_SG_TestGameMode',R,u.Blueprint,factory)
    u.EditorAssetLibrary.set_metadata_tag(bp,'AuthoringOwner','StoneGolemTestV1')
else:
    bp=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(bp,'AuthoringOwner')=='StoneGolemTestV1'
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
cdo.set_editor_property('character_class_info',u.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_CharacterClassInfo'))
cdo.set_editor_property('ability_info',u.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo'))
cdo.set_editor_property('default_pawn_class',u.DefaultPawn.static_class())
cdo.set_editor_property('player_controller_class',u.PlayerController.static_class())
cdo.set_editor_property('player_state_class',u.PlayerState.static_class())
u.BlueprintEditorLibrary.compile_blueprint(bp);assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
u.EditorLoadingAndSavingUtils.new_blank_map(False)
world=ed.get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',bp.generated_class())
ss=u.get_editor_subsystem(u.EditorActorSubsystem)
floor=ss.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-5))
floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
floor.set_actor_scale3d(u.Vector(30,30,.1));floor.set_actor_location(u.Vector(0,0,-5),False,False)
floor.set_actor_label('SG_CombatProbe_Floor');floor.set_editor_property('tags',['SGCombatProbe'])
golem=ss.spawn_actor_from_class(u.EditorAssetLibrary.load_blueprint_class(R+'/BP_StoneGolemElite'),u.Vector(0,0,89))
golem.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
golem.set_editor_property('tags',['Enemy','SGCombatProbe','SGSource'])
golem.set_actor_label('SG_CombatProbe_Source')
for label,position,team in [('Target',u.Vector(100,0,89),'Player'),('Friend',u.Vector(100,100,89),'Enemy'),('Outside',u.Vector(700,0,89),'Player')]:
    actor=ss.spawn_actor_from_class(u.EnemyCharacter,position)
    actor.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
    actor.set_editor_property('tags',[team,'SGCombatProbe',label])
    actor.set_actor_label('SG_CombatProbe_'+label)
ss.clear_actor_selection_set()
