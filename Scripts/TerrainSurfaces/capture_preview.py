"""Render the actual Unreal scene to PNG with a temporary native SceneCapture."""
import unreal as _ts_u

def _ts_begin_capture():
    sub=_ts_u.get_editor_subsystem(_ts_u.EditorActorSubsystem)
    world=_ts_u.get_editor_subsystem(_ts_u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_name()=='L_TerrainSurfacePreview'
    assert not any(a.get_actor_label()=='TS_TemporaryCapture' for a in sub.get_all_level_actors())
    actor=sub.spawn_actor_from_class(_ts_u.SceneCapture2D,_ts_u.Vector(1200,-1200,3100),_ts_u.Rotator(pitch=-60,yaw=90,roll=0))
    actor.set_actor_label('TS_TemporaryCapture')
    comp=actor.get_component_by_class(_ts_u.SceneCaptureComponent2D)
    comp.set_editor_property('capture_every_frame',False)
    comp.set_editor_property('capture_on_movement',False)
    comp.set_editor_property('capture_source',_ts_u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property('fov_angle',65.0)
    target=_ts_u.RenderingLibrary.create_render_target2d(world,1800,1200,_ts_u.TextureRenderTargetFormat.RTF_RGBA8)
    comp.set_editor_property('texture_target',target)
    comp.capture_scene()

_ts_capture_frames=0
def _ts_finish_capture(dt):
    global _ts_capture_frames
    _ts_capture_frames+=1
    if _ts_capture_frames<12: return
    _ts_u.unregister_slate_post_tick_callback(_ts_capture_handle)
    from pathlib import Path
    sub=_ts_u.get_editor_subsystem(_ts_u.EditorActorSubsystem)
    world=_ts_u.get_editor_subsystem(_ts_u.UnrealEditorSubsystem).get_editor_world()
    actor=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='TS_TemporaryCapture')
    comp=actor.get_component_by_class(_ts_u.SceneCaptureComponent2D)
    out=Path(_ts_u.Paths.project_dir()).resolve()/'Saved/TerrainSurfaces'
    _ts_u.RenderingLibrary.export_render_target(world,comp.texture_target,str(out),'TerrainSurfaces_Preview.png')
    sub.destroy_actor(actor)
    _ts_u.log('SURFACE_RENDER_SAVED '+str(out/'TerrainSurfaces_Preview.png'))

_ts_begin_capture()
_ts_capture_handle=_ts_u.register_slate_post_tick_callback(_ts_finish_capture)
