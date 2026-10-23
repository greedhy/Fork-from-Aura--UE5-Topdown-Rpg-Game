"""Normalize transforms and lighting on this task's owned terrain actors only."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
plan = json.loads((root/'Saved/LevelAuthoring/DungeonLabyrinth/layout.json').read_text())
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().split('.')[0] == plan['level']
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
owned = {a.get_actor_label(): a for a in sub.get_all_level_actors() if unreal.Name('DL_Terrain') in a.tags}
with unreal.ScopedEditorTransaction('Refine dungeon terrain transforms and lights'):
    for i, edge in enumerate(plan['walls']):
        yaw = 0 if edge['axis'] == 'x' else 90
        for prefix in ['Wall_', 'WallCollision_']:
            owned['DL_'+prefix+'%03d'%i].set_actor_rotation(unreal.Rotator(pitch=0,yaw=yaw,roll=0),False)
    owned['DL_PlayerStart'].set_actor_rotation(unreal.Rotator(pitch=0,yaw=90,roll=0),False)
    for name, intensity, pitch, yaw, priority in [('KeyLight',18,-55,-35,1),('FillLight',6,-45,145,0)]:
        actor = owned['DL_'+name]
        actor.set_actor_rotation(unreal.Rotator(pitch=pitch,yaw=yaw,roll=0),False)
        comp = actor.get_component_by_class(unreal.DirectionalLightComponent)
        comp.set_intensity(intensity)
        comp.set_editor_property('forward_shading_priority',priority)
    for actor in owned.values():
        if actor.get_actor_label().startswith('DL_RoomGlow_'):
            actor.get_component_by_class(unreal.PointLightComponent).set_intensity(1800)
sub.clear_actor_selection_set()
unreal.log('DL_REFINED '+str(len(owned)))
