"""Independent readback of correction scope and blending boundary invariants."""
import json,math,uuid
from pathlib import Path
import unreal as u
R='/Game/BluePrints/Characters/StoneGolem/Animations/'
source=u.load_asset(R+'AS_SG_Slam');asset=u.load_asset(R+'AS_SG_Slam_Contact')
options=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False,evaluate_curves=True)
assert abs(asset.get_play_length()-1.2)<1.e-5
assert asset.get_editor_property('skeleton')==source.get_editor_property('skeleton')
assert not asset.get_editor_property('enable_root_motion') and asset.get_editor_property('force_root_lock')
def qerror(a,b):
    return min(max(abs(x-y) for x,y in zip([a.x,a.y,a.z,a.w],[b.x,b.y,b.z,b.w])),max(abs(x+y) for x,y in zip([a.x,a.y,a.z,a.w],[b.x,b.y,b.z,b.w])))
maximum_position=0.;maximum_untouched_rotation=0.
for sample in range(145):
    t=sample/120
    a=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options)
    b=u.AnimPoseExtensions.get_anim_pose_at_time(source,t,options)
    for bone in u.AnimPoseExtensions.get_bone_names(b):
        x=u.AnimPoseExtensions.get_bone_pose(a,bone,u.AnimPoseSpaces.LOCAL)
        y=u.AnimPoseExtensions.get_bone_pose(b,bone,u.AnimPoseSpaces.LOCAL)
        error=(x.translation-y.translation).length()
        maximum_position=max(maximum_position,error)
        assert error<.001 and (x.scale3d-y.scale3d).length()<.001, str(bone)
        if str(bone) not in ['spine_01','upperarm_r'] or t<=8/30 or t>=32/30:
            error=qerror(x.rotation,y.rotation)
            maximum_untouched_rotation=max(maximum_untouched_rotation,error)
            assert error<.0001, str(bone)
    assert set(map(str,u.AnimPoseExtensions.get_curve_names(a)))==set(map(str,u.AnimPoseExtensions.get_curve_names(b)))
    for curve in u.AnimPoseExtensions.get_curve_names(b):
        assert abs(u.AnimPoseExtensions.get_curve_weight(a,curve)-u.AnimPoseExtensions.get_curve_weight(b,curve))<.001
report={'run_id':uuid.uuid4().hex,'passed':True,'samples':145,'modified_rotation_tracks':['spine_01','upperarm_r'],'maximum_local_translation_error_cm':maximum_position,'maximum_unchanged_quaternion_component_error':maximum_untouched_rotation,'unmodified_boundary_frames':[0,8,32,36],'curves_preserved':True,'root_motion':False}
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemBuild/contact-variant-verification.json').write_text(json.dumps(report,indent=2))
