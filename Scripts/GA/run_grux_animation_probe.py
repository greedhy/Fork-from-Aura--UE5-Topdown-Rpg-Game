"""Sample actual source AnimBP slot output, feet and weapon bones."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
root=Path(u.Paths.project_dir());out=root/'Saved/GAAuthoring/GruxDesign/runtime-animation.json'
perf=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'));old=perf.get_editor_property('bThrottleCPUWhenNotForeground');perf.set_editor_property('bThrottleCPUWhenNotForeground',False)
mapping={'PrimaryAttack_LA':'Left','PrimaryAttack_RA':'Right','Stampede_Knockup':'Uppercut','Ultimate_Roar':'Roar'}
report={'run_id':uuid.uuid4().hex,'status':'running','clips':{}};entries=[]
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Character):
 if not a.actor_has_tag('GruxAnimationProbe'):continue
 name=next(x for x in mapping if a.actor_has_tag(x));m=a.get_component_by_class(u.SkeletalMeshComponent);anim=m.get_anim_instance();assert anim
 montage=u.load_asset('/Game/BluePrints/Characters/Grux/Expansion/Animations/AM_Grux_'+mapping[name]);assert montage
 a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
 r={'played':anim.montage_play(montage,1.),'anim_class':anim.get_class().get_path_name(),'samples':[]};report['clips'][name]=r;entries.append((a,m,anim,montage,r))
assert len(entries)==4
start=time.monotonic();out.write_text(json.dumps(report))
def tick(dt):
 try:
  for a,m,anim,montage,r in entries:
   bones={}
   for b in ['root','hand_l','hand_r','weapon_l','weapon_r','foot_l','foot_r']:
    v=a.get_actor_transform().inverse_transform_location(m.get_socket_location(b));bones[b]=[v.x,v.y,v.z]
   r['samples'].append({'position':anim.montage_get_position(montage),'active':anim.montage_is_active(montage),'bones':bones})
  if time.monotonic()-start<2.5:return
  report.update(status='complete',passed=all(r['played']>0 and any(s['position']>.5 for s in r['samples']) for r in report['clips'].values()))
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 u.unregister_slate_post_tick_callback(grux_anim_handle);perf.set_editor_property('bThrottleCPUWhenNotForeground',old);out.write_text(json.dumps(report,indent=2))
grux_anim_handle=u.register_slate_post_tick_callback(tick)
