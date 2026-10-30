"""Restore the saved editor map after stopping this task's isolated simulation."""
import json
from pathlib import Path
import unreal as u
assert not u.EditorLevelLibrary.get_game_world(), 'Stop the isolated simulation first'
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().startswith('/Temp/'), 'Refusing to replace a non-probe map'
assert any(a.actor_has_tag('SGAnimationProbe') for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
state=json.loads((Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemBuild/probe-restore.json').read_text())
assert state['map'].startswith('/Game/')
assert u.EditorLoadingAndSavingUtils.load_map(state['map'])
pitch,yaw,roll=state['rotation']
u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(*state['location']),u.Rotator(pitch=pitch,yaw=yaw,roll=roll))
