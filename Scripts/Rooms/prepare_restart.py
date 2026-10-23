def main():
    import unreal as u
    import json
    from pathlib import Path
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    assert not dirty,[p.get_name() for p in dirty]
    root=Path(u.Paths.project_dir()).resolve()
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    marker=root/'Saved/Rooms/restart.json'
    if not marker.exists(): marker.write_text(json.dumps({'map':world.get_path_name().split('.')[0],'dirty':[]}))
    u.SystemLibrary.quit_editor()
main()
