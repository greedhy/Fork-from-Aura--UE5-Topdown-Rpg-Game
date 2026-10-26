import unreal as u, json
from pathlib import Path

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
report = {
    'map': world.get_path_name(),
    'mode': str(world.get_world_settings().get_editor_property('default_game_mode')),
    'dirty_maps': [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    'dirty_content': [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    'mass_groups': [{'label':a.get_actor_label(), 'count':a.get_editor_property('count'),
                     'monster_type':a.get_editor_property('monster_type').get_path_name()}
                    for a in actors if isinstance(a,u.PureMassSpawnRegion)],
    'actors': [{'label': a.get_actor_label(), 'class': a.get_class().get_path_name(),
                'position': str(a.get_actor_location()), 'bounds':str(a.get_actor_bounds(True))} for a in actors if u.Name('DL_Terrain') not in a.tags],
}
out = Path(u.Paths.project_dir(), 'Saved/PureMass/Labyrinth200')
out.mkdir(parents=True, exist_ok=True)
(out/'inspection.json').write_text(json.dumps(report, indent=2), encoding='utf8')
