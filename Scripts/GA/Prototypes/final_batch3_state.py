import unreal as u, json
from pathlib import Path
def _prototype_final_state():
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    state={'map':u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name(),
           'dirty_packages':[p.get_name() for p in dirty],
           'pie_players':len([p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name()])}
    (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch3/final-editor-state.json').write_text(json.dumps(state,indent=2))
_prototype_final_state()
