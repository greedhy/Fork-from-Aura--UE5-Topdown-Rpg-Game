"""Author an isolated contact variant; preserve crop and imported source assets."""
import math,json,uuid,shutil,hashlib,runpy
from pathlib import Path
import unreal as u

assert not u.EditorLevelLibrary.get_game_world(), 'PIE must be stopped'
R='/Game/BluePrints/Characters/StoneGolem/Animations/'
target=R+'AS_SG_Slam_Contact'
project=Path(u.Paths.project_dir()).resolve()
out=project/'Saved/GAAuthoring/StoneGolemBuild'
run=uuid.uuid4().hex
backup=out/run;backup.mkdir()
assert target not in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
source=u.load_asset(R+'AS_SG_Slam')
assert R+'AS_SG_Slam' not in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}, 'Source clip has unsaved edits'
assert abs(source.get_play_length()-1.2)<1.e-5
assert abs(u.AnimationLibrary.get_time_at_frame(source,1)-1/30)<1.e-6
assert u.EditorAssetLibrary.get_metadata_tag(source,'SourceFrameRange')=='27:63'
assert u.EditorAssetLibrary.get_metadata_tag(source,'SourceClip')=='/Game/StoneGolem/Animations/AS_StoneGolem_attack5'
mesh=u.load_asset('/Game/StoneGolem/Mesh/SM_StoneGolem_Hammer')
vertices=[]
for section in range(mesh.get_num_sections(0)):
    vertices.extend(u.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,section)[0])
assert vertices
opt=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False)

def multiply(a,b):
    return u.Quat(x=a.w*b.x+a.x*b.w+a.y*b.z-a.z*b.y,
                  y=a.w*b.y-a.x*b.z+a.y*b.w+a.z*b.x,
                  z=a.w*b.z+a.x*b.y-a.y*b.x+a.z*b.w,
                  w=a.w*b.w-a.x*b.x-a.y*b.y-a.z*b.z)

def corrected(t,degrees):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(source,t,opt)
    parent=u.AnimPoseExtensions.get_bone_pose(pose,'pelvis',u.AnimPoseSpaces.WORLD)
    edits={}
    for bone in ['spine_01','spine_02','spine_03','spine_04','spine_05','clavicle_r','upperarm_r','lowerarm_r','hand_r','weapon_r']:
        local=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL)
        rotation=multiply(parent.rotation,local.rotation)
        if bone in ['spine_01','upperarm_r']:
            rad=math.radians(degrees*(.75 if bone=='spine_01' else .25))/2
            rotation=multiply(u.Quat(x=math.sin(rad),y=0,z=0,w=math.cos(rad)),rotation)
            q=parent.rotation
            local.rotation=multiply(u.Quat(x=-q.x,y=-q.y,z=-q.z,w=q.w),rotation)
            edits[bone]=local
        next_transform=u.Transform()
        next_transform.translation=parent.transform_location(local.translation)
        next_transform.rotation=rotation
        next_transform.scale3d=u.Vector(1,1,1)
        parent=next_transform
    return pose,edits,parent

def height(pose):
    if isinstance(pose,tuple):
        original,_,new_weapon=pose
        old_weapon=u.AnimPoseExtensions.get_bone_pose(original,'weapon_r',u.AnimPoseSpaces.WORLD)
        socket=u.AnimPoseExtensions.get_socket_pose(original,'weapon_rSocket',u.AnimPoseSpaces.WORLD)
        return min(new_weapon.transform_location(old_weapon.inverse_transform_location(socket.transform_location(v))).z for v in vertices)
    tr=u.AnimPoseExtensions.get_socket_pose(pose,'weapon_rSocket',u.AnimPoseSpaces.WORLD)
    return min(tr.transform_location(v).z for v in vertices)

before=height(corrected(.7,0))

assert 25<before<31, 'Unexpected source; re-inspect contact'
assert height(corrected(.7,-55))<1.5, 'No reachable contact in allowed rotation range'
lo,hi=-55.,0.
for _ in range(24):
    mid=(lo+hi)/2
    if height(corrected(.7,mid))<1.5:lo=mid
    else:hi=mid
angle=(lo+hi)/2

def weight(frame):
    if frame<=8 or frame>=32:return 0.
    x=(frame-8)/13 if frame<=21 else (32-frame)/11
    return x*x*x*(x*(x*6-15)+10)

keys={bone:[] for bone in ['spine_01','upperarm_r']}
for frame in range(37):
    pose=corrected(frame/30,angle*weight(frame))
    for bone in keys:
        keys[bone].append(pose[1][bone])
protected=[project/'Content/StoneGolem/Animations/AS_StoneGolem_attack5.uasset',project/'Content/BluePrints/Characters/StoneGolem/Animations/AS_SG_Slam.uasset']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
existing=u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else None
if existing:
    assert u.EditorAssetLibrary.get_metadata_tag(existing,'AuthoringOwner')=='StoneGolemContactV1'
    file=project/'Content/BluePrints/Characters/StoneGolem/Animations/AS_SG_Slam_Contact.uasset'
    shutil.copy2(file,backup/file.name)
asset=existing or u.EditorAssetLibrary.duplicate_asset(source.get_path_name(),target)
assert asset
controller=asset.get_editor_property('controller')
controller.open_bracket('StoneGolem ground contact correction')
try:
    for bone,transforms in keys.items():
        assert controller.set_bone_track_keys(bone,[t.translation for t in transforms],[t.rotation for t in transforms],[t.scale3d for t in transforms])
finally:controller.close_bracket()
u.EditorAssetLibrary.set_metadata_tag(asset,'AuthoringOwner','StoneGolemContactV1')
u.EditorAssetLibrary.set_metadata_tag(asset,'ContactCorrectionDegrees',str(angle))
u.EditorAssetLibrary.set_metadata_tag(asset,'ContactCorrectionBones','spine_01:0.75,upperarm_r:0.25')
u.EditorAssetLibrary.set_metadata_tag(asset,'ContactCorrectionSource',source.get_path_name())
# Independent half-frame geometry and invariant validation before saving.
rows=[];max_foot_error=0.
for sample in range(73):
    t=sample/60
    actual=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,opt)
    old=u.AnimPoseExtensions.get_anim_pose_at_time(source,t,opt)
    for bone in ['root','pelvis','foot_l','foot_r','ball_l','ball_r']:
        a=u.AnimPoseExtensions.get_bone_pose(actual,bone,u.AnimPoseSpaces.WORLD)
        b=u.AnimPoseExtensions.get_bone_pose(old,bone,u.AnimPoseSpaces.WORLD)
        error=(a.translation-b.translation).length()
        max_foot_error=max(max_foot_error,error)
        assert error<.001, f'Lower-body drift: {bone}'
    rows.append({'time':t,'minimum_hammer_z':height(actual)})
assert min(row['minimum_hammer_z'] for row in rows)>-.5, 'Ground penetration'
assert abs(rows[42]['minimum_hammer_z']-1.5)<.1
# Verify the entire retained clip before saving, including on re-entry.
runpy.run_path(str(project/'Scripts/GA/StoneGolem/verify_contact_variant.py'))
assert u.EditorAssetLibrary.save_loaded_asset(asset,False)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
(out/'contact-correction.json').write_text(json.dumps({'run_id':run,'saved':True,'asset':target,'angle_degrees':angle,'original_gap_cm':before,'contact_gap_cm':rows[42]['minimum_hammer_z'],'max_lower_body_position_error_cm':max_foot_error,'source_hashes':hashes,'rows':rows},indent=2))

