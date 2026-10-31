import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
u.GameplayStatics.set_global_time_dilation(w,.25)
actors=[a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter) if a.actor_has_tag('LegacyAnimationProbe')]
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};entries=[]
for a in actors:
 name=next(n for n in ['Spear','Sling','GhoulL','GhoulR'] if a.actor_has_tag(n))
 a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
 m=next(c for c in a.get_components_by_class(u.SkeletalMeshComponent) if c.get_name()=='CharacterMesh0');anim=m.get_anim_instance()
 montage=u.load_asset('/Game/BluePrints/Characters/LegacyExpansion/Animations/AM_Legacy_'+name)
 r={'name':name,'played':anim.montage_play(montage,1.),'samples':[],'mesh':str(m.get_relative_transform()),'attachments':[]}
 for c in a.get_components_by_class(u.SkeletalMeshComponent):
  r['attachments'].append({'name':c.get_name(),'socket':str(c.get_attach_socket_name()),'mesh':str(c.get_editor_property('skeletal_mesh_asset'))})
 report['cases'].append(r);entries.append((a,m,anim,montage,r))
out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/LegacyMonsterDesign/runtime-animation.json';start=u.GameplayStatics.get_time_seconds(w)
def tick(dt):
 for a,m,anim,montage,r in entries:
  tr=a.get_actor_transform();points={}
  for b in ['Hand-L','Hand-R','LeftHandSocket','RightHandSocket','Foot-L','Foot-R']:
   if m.does_socket_exist(b):
    v=tr.inverse_transform_location(m.get_socket_location(b));points[b]=[v.x,v.y,v.z]
  weapon=a.get_editor_property('weapon')
  if weapon and weapon.get_editor_property('skeletal_mesh_asset'):
   v=tr.inverse_transform_location(weapon.get_socket_location('TipSocket'));points['WeaponTip']=[v.x,v.y,v.z]
  r['samples'].append({'t':u.GameplayStatics.get_time_seconds(w)-start,'position':anim.montage_get_position(montage),'points':points})
 if u.GameplayStatics.get_time_seconds(w)-start>2.3:
  report['status']='complete';report['passed']=all(r['played']>0 and len({round(s['position'],2) for s in r['samples']})>10 for r in report['cases'])
  u.GameplayStatics.set_global_time_dilation(w,1.);u.unregister_slate_post_tick_callback(handle)
  out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
