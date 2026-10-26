"""Capture the actual local player's viewport, not the editor's terrain viewport."""
import unreal as u, time
from pathlib import Path

_cap_settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
_cap_old=_cap_settings.get_editor_property('bThrottleCPUWhenNotForeground')
_cap_settings.set_editor_property('bThrottleCPUWhenNotForeground',False)
_cap_pc=next(p for p in u.ObjectIterator(u.PureMassPlayerController) if 'UEDPIE_' in p.get_path_name() and p.is_local_controller() and p.get_controlled_pawn())
_cap_path=Path(u.Paths.project_dir(),'Saved/PureMass/Labyrinth200/gameplay.png').resolve().as_posix()
u.SystemLibrary.execute_console_command(_cap_pc.get_world(),'HighResShot 1 filename="'+_cap_path+'"',_cap_pc)
_cap_start=time.monotonic()
def _cap_tick(dt):
    if time.monotonic()-_cap_start<3:return
    _cap_settings.set_editor_property('bThrottleCPUWhenNotForeground',_cap_old)
    u.unregister_slate_post_tick_callback(_cap_handle)
_cap_handle=u.register_slate_post_tick_callback(_cap_tick)
