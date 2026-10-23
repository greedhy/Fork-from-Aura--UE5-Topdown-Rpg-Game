"""Populate only the dedicated new level. Execute through Unreal MCP console_exec."""
import json
import math
import uuid
from collections import Counter
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
report_root = root / 'Saved/LevelAuthoring/DungeonLabyrinth'
plan = json.loads((report_root / 'layout.json').read_text(encoding='utf8'))
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().split('.')[0] == plan['level'], 'Wrong target world'
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert not any('DL_Terrain' in [str(t) for t in a.tags] for a in actors.get_all_level_actors()), 'Already populated; inspect before rerunning'
run = report_root / str(uuid.uuid4())
run.mkdir()
counts = Counter()
cache = {}
CELL = plan['cell_cm']
OX, OY = plan['origin_cm']

def mesh_asset(name):
    if name not in cache:
        cache[name] = unreal.load_asset('/Game/Assets/Dungeon/' + name)
        assert cache[name], name
    return cache[name]

def register(actor, label, folder):
    actor.set_actor_label('DL_' + label)
    actor.set_folder_path('DungeonLabyrinth/' + folder)
    actor.tags = [unreal.Name('DL_Terrain')]
    counts[folder] += 1
    return actor

def box(name, label, cx, cy, base, sx, sy, sz, folder, yaw=0, hidden=False):
    mesh = mesh_asset(name)
    bounds = mesh.get_bounding_box()
    size = bounds.max - bounds.min
    scale = unreal.Vector(sx / size.x, sy / size.y, sz / size.z if size.z > .1 else 1)
    mx = (bounds.min.x + bounds.max.x) * .5 * scale.x
    my = (bounds.min.y + bounds.max.y) * .5 * scale.y
    angle = math.radians(yaw)
    pos = unreal.Vector(cx - mx*math.cos(angle) + my*math.sin(angle),
                        cy - mx*math.sin(angle) - my*math.cos(angle), base - bounds.min.z*scale.z)
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, pos, unreal.Rotator(pitch=0, yaw=yaw, roll=0))
    comp = actor.static_mesh_component
    comp.set_static_mesh(mesh)
    actor.set_actor_scale3d(scale)
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    comp.set_collision_profile_name('BlockAll')
    # Walls in this kit lack simple collision. Dedicated hidden stone blocks
    # provide simple collision without editing the shared source mesh assets.
    if hidden:
        comp.set_visibility(False)
        comp.set_editor_property('cast_shadow', False)
        actor.set_actor_hidden_in_game(True)
    register(actor, label, folder)
    return actor

with unreal.ScopedEditorTransaction('Build dungeon labyrinth terrain'):
    for i, t in enumerate(plan['tiles']):
        width = t['size'] * CELL
        cx, cy = OX + (t['x'] + t['size']/2)*CELL, OY + (t['y'] + t['size']/2)*CELL
        box('SM_Block4x4x1', 'Foundation_%03d' % i, cx, cy, -220, width, width,
            220 + t['z'], 'Foundations')
        tile_name = {1: 'SM_Tile_2x2', 2: 'SM_Tile_4x4', 3: 'SM_Tile_6x6'}[t['size']]
        box(tile_name, 'Floor_%03d_%s' % (i, t['zone']), cx, cy, t['z'] + 1,
            width, width, 1, 'Floors/' + t['zone'])
    for i, e in enumerate(plan['walls']):
        horizontal = e['axis'] == 'x'
        cx = OX + (e['at'] + e['count']/2)*CELL if horizontal else OX + e['line']*CELL
        cy = OY + e['line']*CELL if horizontal else OY + (e['at'] + e['count']/2)*CELL
        length, yaw = e['count'] * CELL, 0 if horizontal else 90
        box('SM_Wall_4x2' if e['count'] == 2 else 'SM_Wall_2x2',
            'Wall_%03d' % i, cx, cy, e['z'], length, 100, 280, 'Walls', yaw)
        box('SM_Block4x4x1', 'WallCollision_%03d' % i, cx, cy, e['z'], length, 100,
            280, 'Collision', yaw, True)
    stair = plan['stair']
    for i in range(stair['steps']):
        depth = stair['run'] / stair['steps']
        top = (i + 1) * stair['rise'] / stair['steps']
        cx = OX + stair['x']*CELL + stair['width']/2
        cy = OY + stair['y']*CELL + (i+.5)*depth
        box('SM_Block4x4x1', 'Stair_%02d' % i, cx, cy, -220, stair['width'], depth,
            220+top, 'Stairs')
        box('SM_Tile_4x4', 'StairTread_%02d' % i, cx, cy, top+1,
            stair['width'], depth, 1, 'Stairs')
    for i, (x, y) in enumerate([(10.1, 16.1), (14.9, 16.1), (10.1, 19.9), (14.9, 19.9),
                                (10.1, 25.1), (14.9, 25.1), (10.1, 27.9), (14.9, 27.9)]):
        z = 200 if y > 24 else 0
        box('SM_Block_1x1x2', 'Pillar_%02d' % i, OX+x*CELL, OY+y*CELL, z,
            160, 160, 400, 'Pillars')
    # Existing kit and materials only; lighting makes the terrain readable.
    for label, intensity, rotation, color, shadows in [
        ('KeyLight', 18.0, unreal.Rotator(pitch=-55, yaw=-35, roll=0), unreal.LinearColor(1,.86,.68), True),
        ('FillLight', 6.0, unreal.Rotator(pitch=-45, yaw=145, roll=0), unreal.LinearColor(.5,.67,1), False),
    ]:
        light = register(actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,3000), rotation), label, 'Lighting')
        comp = light.get_component_by_class(unreal.DirectionalLightComponent)
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_intensity(intensity)
        comp.set_light_color(color)
        comp.set_editor_property('cast_shadows', shadows)
        comp.set_editor_property('light_source_angle', 8.0)
        comp.set_editor_property('forward_shading_priority', 1 if shadows else 0)
    for i, room in enumerate(plan['rooms']):
        x0, y0, x1, y1 = room['bounds']
        x, y = OX+(x0+x1+1)*CELL/2, OY+(y0+y1+1)*CELL/2
        light = register(actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(x,y,room['z']+450)), 'RoomGlow_%02d' % i, 'Lighting')
        comp = light.get_component_by_class(unreal.PointLightComponent)
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_intensity(1800)
        comp.set_light_color(unreal.LinearColor(1,.43,.12))
        comp.set_attenuation_radius(1800)
        comp.set_editor_property('cast_shadows', False)
        marker = register(actors.spawn_actor_from_class(unreal.TargetPoint, unreal.Vector(x,y,room['z']+100)), room['name'], 'LayoutMarkers')
    start = plan['start_cell']
    ps = register(actors.spawn_actor_from_class(unreal.PlayerStart,
        unreal.Vector(OX+(start[0]+.5)*CELL, OY+(start[1]+.5)*CELL, 110), unreal.Rotator(pitch=0,yaw=90,roll=0)), 'PlayerStart', 'GameplaySetup')
    ps.set_editor_property('player_start_tag', unreal.Name('PlayerStart'))
    nav = register(actors.spawn_actor_from_class(unreal.NavMeshBoundsVolume,
        unreal.Vector(-200,0,300)), 'NavMeshBounds', 'GameplaySetup')
    nav.set_actor_scale3d(unreal.Vector(52,62,9))
    world.get_world_settings().set_editor_property('default_game_mode',
        unreal.load_class(None, '/Game/BluePrints/Game/BP_MyGameMode.BP_MyGameMode_C'))
    settings = world.get_world_settings()
    settings.set_editor_property('kill_z', -3000.0)

result = {'run_id': run.name, 'level': plan['level'], 'counts': dict(counts),
          'actors_created': sum(counts.values()), 'used_meshes': sorted(cache),
          'layout_cells': len(plan['cells']), 'reachable_cells': plan['reachable_cells'],
          'phase': 'terrain layout; no enemies or interactable content placed'}
(run/'build-result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
(report_root/'latest-build.json').write_text(json.dumps(result,indent=2),encoding='utf8')
unreal.log('DUNGEON_TERRAIN_BUILT ' + json.dumps(result))
