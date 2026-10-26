def _restore_labyrinth():
    import unreal as u,json
    from pathlib import Path
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    assert not dirty,[p.get_name() for p in dirty]
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/levels/L_DungeonLabyrinth')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    result={'map':world.get_path_name(),'dirty':[],'net_allow_pie_seamless_travel':u.SystemLibrary.get_console_variable_int_value('net.AllowPIESeamlessTravel')}
    (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/restoration.json').write_text(json.dumps(result,indent=2),encoding='utf8')
_restore_labyrinth()
