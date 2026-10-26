"""Configure the explicitly requested labyrinth map; reuse PureMass code/assets unchanged."""
import unreal as u, json, math, shutil
from pathlib import Path

def main():
    root = Path(u.Paths.project_dir()).resolve()
    out = root/'Saved/PureMass/Labyrinth200'
    out.mkdir(parents=True, exist_ok=True)
    level = '/Game/levels/L_DungeonLabyrinth'
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0] == level
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Save existing map edits first'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Save existing asset edits first'
    backup = out/'L_DungeonLabyrinth-before-200.umap'
    if not backup.exists(): shutil.copy2(root/'Content/levels/L_DungeonLabyrinth.umap', backup)
    editor = u.get_editor_subsystem(u.EditorActorSubsystem)
    assert not u.GameplayStatics.get_all_actors_of_class(world, u.EnemyCharacter)
    assert not u.GameplayStatics.get_all_actors_of_class(world, u.MyEnemySpawnPoint)
    monster = u.load_asset('/Game/PureMass/DA_MassGoblin')
    mode = u.load_class(None, '/Game/PureMass/BP_PureMassGameMode.BP_PureMassGameMode_C')
    assert monster and mode
    # Room bounds come from the authored dungeon layout, in 400 cm cells.
    rooms = [
        ('02_Crossroads', (9,7,15,11), 0, 40),
        ('03_WestCrypt', (1,7,5,11), 0, 30),
        ('04_EastGallery', (19,7,23,13), 0, 40),
        ('05_CentralCourt', (9,15,15,20), 0, 40),
        ('06_UpperVault', (19,19,23,23), 0, 25),
        ('07_RaisedSanctum', (9,24,15,28), 200, 25),
    ]
    existing = {a.get_actor_label(): a for a in u.GameplayStatics.get_all_actors_of_class(world, u.PureMassSpawnRegion)}
    labels = {'Mass200_'+name for name, bounds, z, count in rooms}
    assert set(existing).issubset(labels), 'Unexpected existing Mass groups; do not silently add extra monsters'
    spacing = 160.0
    planned = []
    for name, (x0,y0,x1,y1), z, count in rooms:
        cols = math.ceil(math.sqrt(count)); rows = math.ceil(count/cols)
        x = -5000+(x0+x1+1)*200-(cols-1)*spacing/2
        y = -5800+(y0+y1+1)*200-(rows-1)*spacing/2
        if name == '07_RaisedSanctum':
            x += 400  # Between the return portal mesh and the room's corner pillar.
            y += 300
        points = []
        for i in range(count):
            pos = u.Vector(x+(i%cols)*spacing, y+(i//cols)*spacing, z+61)
            hit = u.SystemLibrary.line_trace_single(world, pos+u.Vector(0,0,80), pos-u.Vector(0,0,100),
                u.TraceTypeQuery.ECC_VISIBILITY, False, [], u.DrawDebugTrace.NONE)
            values = hit.to_tuple() if hit else None
            assert values and values[0] and abs(values[4].z-z)<5, (name,i,'floor',str(values))
            points.append([pos.x,pos.y,pos.z])
        target = u.Vector(x+spacing,y+spacing,z+20)
        path = u.NavigationSystemV1.find_path_to_location_synchronously(world,u.Vector(0,-4800,30),target)
        assert path and path.is_valid() and not path.is_partial(), (name,'navigation')
        planned.append({'room':name,'count':count,'origin':[x,y,z+61],'points':points})
    assert sum(p['count'] for p in planned)==200
    for p in planned:
        label = 'Mass200_'+p['room']
        actor = existing.get(label) or editor.spawn_actor_from_class(u.PureMassSpawnRegion,u.Vector(*p['origin']))
        assert actor
        actor.set_actor_label(label)
        actor.set_actor_location(u.Vector(*p['origin']),False,True)
        actor.set_editor_property('monster_type',monster)
        actor.set_editor_property('count',p['count'])
        actor.set_editor_property('spacing',spacing)
        actor.set_editor_property('room_id',p['room'])
        actor.set_folder_path('Mass200/Goblin')
    world.get_world_settings().set_editor_property('default_game_mode',mode)
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    report = {'passed':True,'map':level,'total':200,'groups':planned,'spacing_cm':spacing,
              'validated_floor_points':200,'complete_navigation_routes':6,'game_mode':mode.get_path_name(),
              'backup':str(backup),'unchanged_source_code':True}
    (out/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    u.log('LABYRINTH_200_AUTHORED')

main()
