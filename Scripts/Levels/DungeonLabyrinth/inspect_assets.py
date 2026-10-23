"""Read the existing dungeon kit and reference level through Unreal MCP Python."""
import json
from collections import Counter
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = root / 'Saved/LevelAuthoring/DungeonLabyrinth'
out.mkdir(parents=True, exist_ok=True)
names = ['SM_Tile1x1_A', 'SM_Tile_2x2', 'SM_Tile_4x4', 'SM_Tile_6x6',
         'SM_Tile_6x9', 'SM_Wall_2x1', 'SM_Wall_2x2', 'SM_Wall_4x2',
         'SM_Wall_U', 'SM_Block_1x1x1', 'SM_Block_1x1x2', 'SM_Block4x4x1',
         'SM_Stairs', 'SM_Stairs_nobottom', 'SM_DungeonEntrance_Doorway',
         'SM_DungeonEntrance_Stair', 'SM_TilesetEdge_nobase_4', 'SM_Corner_wall_short']
def xyz(v):
    return [v.x, v.y, v.z]
meshes = {}
for name in names:
    mesh = unreal.load_asset('/Game/Assets/Dungeon/' + name)
    bounds = mesh.get_bounding_box()
    meshes[name] = {'path': mesh.get_path_name(), 'min': xyz(bounds.min), 'max': xyz(bounds.max),
                    'materials': [str(m.material_interface) for m in mesh.static_materials]}
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
usage, examples = Counter(), []
lights = []
for actor in actors:
    if isinstance(actor, unreal.StaticMeshActor):
        mesh = actor.static_mesh_component.static_mesh
        if mesh and '/Dungeon/' in mesh.get_path_name():
            usage[mesh.get_name()] += 1
            if len(examples) < 12:
                examples.append({'mesh': mesh.get_name(), 'label': actor.get_actor_label(),
                                 'location': xyz(actor.get_actor_location()),
                                 'rotation': str(actor.get_actor_rotation()),
                                 'scale': xyz(actor.get_actor_scale3d())})
    if isinstance(actor, (unreal.DirectionalLight, unreal.SkyLight)):
        lights.append({'label': actor.get_actor_label(), 'class': actor.get_class().get_name(),
                       'rotation': str(actor.get_actor_rotation())})
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
result = {'world': world.get_path_name(), 'meshes': meshes, 'reference_usage': dict(usage),
          'examples': examples, 'lights': lights,
          'game_mode': str(world.get_world_settings().get_editor_property('default_game_mode'))}
(out / 'asset-baseline.json').write_text(json.dumps(result, indent=2), encoding='utf8')
unreal.log('DUNGEON_KIT_INSPECTED ' + str(out / 'asset-baseline.json'))
