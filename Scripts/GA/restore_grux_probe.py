import unreal as u,json
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);assert ed.get_editor_world().get_path_name().startswith('/Temp/')
r=json.loads((Path(u.Paths.project_dir())/'Saved/GAAuthoring/GruxDesign/restore.json').read_text())
assert u.EditorLoadingAndSavingUtils.load_map(r['map'])
p,y,roll=r['rotation'];u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(*r['location']),u.Rotator(pitch=p,yaw=y,roll=roll))
