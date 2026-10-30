"""Read-only LOD0 hammer surface gate; bounds alone cannot prove contact."""
import unreal as u,json,uuid
from pathlib import Path
p=Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemBuild'
m=u.load_asset('/Game/StoneGolem/Mesh/SM_StoneGolem_Hammer')
vertices=[]
for section in range(m.get_num_sections(0)):
 vertices.extend(u.ProceduralMeshLibrary.get_section_from_static_mesh(m,0,section)[0])
a=u.load_asset('/Game/BluePrints/Characters/StoneGolem/Animations/AS_SG_Slam_Contact')
rows=[]
for sample in range(145):
 frame=sample/4
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,frame/30,u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.COMPRESSED,should_retarget=False))
 transform=u.AnimPoseExtensions.get_socket_pose(pose,'weapon_rSocket',u.AnimPoseSpaces.WORLD)
 points=[transform.transform_location(v) for v in vertices]
 point=min(points,key=lambda v:v.z)
 rows.append({'frame':frame,'time':frame/30,'lowest_vertex':[point.x,point.y,point.z]})
assert vertices, 'No render vertices returned; do not treat missing geometry as contact'
lowest=min(rows,key=lambda row:row['lowest_vertex'][2])
planned=next(row for row in rows if row['frame']==21)
passed=(-.5<=lowest['lowest_vertex'][2] and -.5<=planned['lowest_vertex'][2]<=2)
(p/'hammer-contact-geometry.json').write_text(json.dumps({'run_id':uuid.uuid4().hex,'asset':a.get_path_name(),'vertex_count':len(vertices),'lowest':lowest,'planned_contact':planned,'reference_floor_z':0,'contact_tolerance_cm':2,'penetration_tolerance_cm':.5,'passed':passed,'rows':rows},indent=2))
