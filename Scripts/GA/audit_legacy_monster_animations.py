"""Inspect real montage clips, notifies, attachment transforms and sampled skeletons."""
import unreal as u,json,uuid
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();folder=root/'Saved/GAAuthoring/LegacyMonsterDesign';folder.mkdir(exist_ok=True)
report={'run_id':uuid.uuid4().hex,'actors':[],'clips':[]};seen=set()
opts=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=False)
for path in ['/Game/BluePrints/Characters/Goblin/BP_GoblinSpear','/Game/BluePrints/Characters/Goblin/BP_Goblin_Slinshot','/Game/BluePrints/Characters/Ghoul/BP_Ghoul']:
 cdo=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(path));row={'path':path,'components':[],'montages':[]}
 for c in cdo.get_components_by_class(u.SceneComponent):
  props={}
  for key in ['relative_location','relative_rotation','relative_scale3d','skeletal_mesh_asset','static_mesh','socket_name']:
   try:props[key]=str(c.get_editor_property(key))
   except Exception:pass
  row['components'].append({'name':c.get_name(),'class':c.get_class().get_path_name(),'properties':props})
 for tagged in cdo.get_editor_property('attack_montage'):
  m=tagged.get_editor_property('montage');mr={'path':m.get_path_name(),'duration':m.get_play_length(),'notifies':[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(m)],'clips':[]}
  for track in m.get_editor_property('slot_anim_tracks'):
   for seg in track.get_editor_property('anim_track').get_editor_property('anim_segments'):
    a=seg.get_editor_property('anim_reference');mr['clips'].append(a.get_path_name())
    if a.get_path_name() in seen:continue
    seen.add(a.get_path_name());ar={'path':a.get_path_name(),'duration':a.get_play_length(),'root_motion':a.get_editor_property('enable_root_motion'),'notifies':[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(a)],'samples':[]}
    for i in range(31):
     t=a.get_play_length()*i/30;p=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opts);bones={}
     for b in u.AnimPoseExtensions.get_bone_names(p):
      if any(x in str(b).lower() for x in ['root','hand','weapon','foot','head']):
       tr=u.AnimPoseExtensions.get_bone_pose(p,b,u.AnimPoseSpaces.WORLD);v=tr.translation;bones[str(b)]=[v.x,v.y,v.z]
     ar['samples'].append({'t':t,'bones':bones})
    report['clips'].append(ar)
  row['montages'].append(mr)
 report['actors'].append(row)
(folder/'source-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
