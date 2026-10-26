import unreal as u, json
from pathlib import Path

out=Path(u.Paths.project_dir(),'Saved/PureMass/PlayerAnimation')
out.mkdir(parents=True,exist_ok=True)
rows=[]
for path in ['/Game/BluePrints/Characters/Player/BP_Player.BP_Player_C','/Game/PureMass/BP_MassPlayer.BP_MassPlayer_C']:
    cls=u.load_class(None,path);cdo=u.get_default_object(cls)
    mesh=cdo.get_component_by_class(u.SkeletalMeshComponent)
    rows.append({'class':path,'mesh':mesh.get_path_name(),'skeletal_mesh':str(mesh.get_editor_property('skeletal_mesh_asset')),
        'animation_mode':str(mesh.get_editor_property('animation_mode')),'anim_class':str(mesh.get_editor_property('anim_class')),
        'pause_anims':mesh.get_editor_property('pause_anims'),'tick_enabled':mesh.get_editor_property('primary_component_tick').get_editor_property('start_with_tick_enabled')})
runtime=[]
for pawn in u.ObjectIterator(u.PureMassPlayerCharacter):
    if 'UEDPIE_' not in pawn.get_path_name():continue
    mesh=pawn.get_component_by_class(u.SkeletalMeshComponent)
    if not mesh:continue
    anim=mesh.get_anim_instance()
    data={'pawn':pawn.get_path_name(),'is_character_actor':isinstance(pawn,u.Character),'anim':str(anim),'velocity':str(pawn.get_velocity()),'mesh_tick':mesh.is_component_tick_enabled(),'variables':{}}
    if anim:
        for name in ['BP_Player_Character','Character Movement','Ground_speed','ShouldRun','Dead','Player','PlayerCharacter','Character','Speed','GroundSpeed','Velocity','IsFalling','IsInAir','bIsInAir']:
            try:data['variables'][name]=str(anim.get_editor_property(name))
            except Exception:pass
    runtime.append(data)
bp=u.load_asset('/Game/BluePrints/Characters/Player/ABP_Player')
reflection={}
for key in ['new_variables','ubergraph_pages']:
    try:reflection[key]=str(bp.get_editor_property(key))
    except Exception as exc:reflection[key]=repr(exc)
(out/'inspection.json').write_text(json.dumps({'assets':rows,'runtime':runtime,'reflection':reflection},indent=2),encoding='utf8')
