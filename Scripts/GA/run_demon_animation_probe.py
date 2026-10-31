"""Measure actual montage output and anatomy in an isolated PIE world."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
actors=[a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter) if a.actor_has_tag('DemonAnimationProbe')]
assert len(actors)==3
report={'run_id':uuid.uuid4().hex,'status':'running','clips':{}}
out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/demon-runtime-animation.json'
perf=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
throttle=perf.get_editor_property('bThrottleCPUWhenNotForeground');perf.set_editor_property('bThrottleCPUWhenNotForeground',False)
entries=[]
for a in actors:
 clip=next(k for k in ['ClawL','ClawR','Tailspin'] if a.actor_has_tag(k))
 mesh=a.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance();assert anim
 montage=u.load_asset('/Game/BluePrints/Characters/Demon/Expansion/Animations/AM_Demon_'+clip)
 a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
 report['clips'][clip]={'played':anim.montage_play(montage,1.),'anim_class':anim.get_class().get_path_name(),'samples':[]}
 entries.append((clip,a,mesh,anim,montage))
out.write_text(json.dumps(report))
start=time.monotonic()
def tick(dt):
 try:
  for clip,a,mesh,anim,montage in entries:
   sample={'position':anim.montage_get_position(montage),'active':anim.montage_is_active(montage),'bones':{}}
   for bone in ['Wrist-L','Wrist-R','Tail_07']:
    v=a.get_actor_transform().inverse_transform_location(mesh.get_socket_location(bone));sample['bones'][bone]=[v.x,v.y,v.z]
   report['clips'][clip]['samples'].append(sample)
  if time.monotonic()-start<2.5:return
  report['status']='complete'
  report['passed']=all(v['played']>0 and any(s['position']>.5 for s in v['samples']) for v in report['clips'].values())
 except Exception as e:report.update(status='failed',error=str(e),passed=False)
 u.unregister_slate_post_tick_callback(handle)
 perf.set_editor_property('bThrottleCPUWhenNotForeground',throttle)
 out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
