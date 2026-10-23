def main():
    import unreal as u
    from pathlib import Path
    import json
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    assert not dirty, 'Editor has unsaved work; stop before restarting: '+str([p.get_name() for p in dirty])
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    root=Path(u.Paths.project_dir()).resolve()
    (root/'Saved/TerrainSurfaces/restart.json').write_text(json.dumps({'map':world.get_path_name().split('.')[0],'dirty_packages':[]}))
    u.SystemLibrary.quit_editor()
main()
