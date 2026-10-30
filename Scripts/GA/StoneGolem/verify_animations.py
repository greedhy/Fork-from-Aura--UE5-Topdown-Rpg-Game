"""Read-only animation gate. Run in the project editor's Python interpreter."""
import json
import uuid
from pathlib import Path
import unreal as u

ROOT = '/Game/BluePrints/Characters/StoneGolem/Animations'
CLIPS = [('AS_SG_Slam', 'AS_StoneGolem_attack5', 27, 63, 21),
         ('AS_SG_ShieldBash', 'AS_StoneGolem_attack2', 0, 33, 25)]


def xyz(v):
    return [v.x, v.y, v.z]

def options(compressed=False):
    return u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.COMPRESSED if compressed else u.AnimDataEvalType.RAW,
                                      should_retarget=False, evaluate_curves=True)


def verify():
    results = []
    for name, source_name, start, end, hit in CLIPS:
        asset = u.load_asset(ROOT + '/' + name)
        source = u.load_asset('/Game/StoneGolem/Animations/' + source_name)
        assert asset and source, 'Missing animation: ' + name
        assert isinstance(asset,u.AnimSequence)
        assert abs(u.AnimationLibrary.get_time_at_frame(asset,1)-1/30)<1.e-6
        assert u.AnimationLibrary.get_num_frames(asset)==end-start
        assert abs(asset.get_play_length() - (end-start)/30) < 1.e-5, name + ' duration'
        assert asset.get_editor_property('skeleton') == source.get_editor_property('skeleton')
        assert not asset.get_editor_property('enable_root_motion')
        assert asset.get_editor_property('force_root_lock')
        assert abs(asset.get_editor_property('rate_scale')-1.) < 1.e-6
        maximum = 0.
        curve_error=0.
        for sample in range((end-start)*2+1):
            frame=sample/2
            old = u.AnimPoseExtensions.get_anim_pose_at_time(source, (start+frame)/30, options())
            new = u.AnimPoseExtensions.get_anim_pose_at_time(asset, frame/30, options())
            old_curves=u.AnimPoseExtensions.get_curve_names(old)
            assert {str(n).casefold() for n in old_curves} == {str(n).casefold() for n in u.AnimPoseExtensions.get_curve_names(new)}
            for curve in old_curves:
                error=abs(u.AnimPoseExtensions.get_curve_weight(old,curve)-u.AnimPoseExtensions.get_curve_weight(new,curve))
                curve_error=max(curve_error,error)
                assert error < .005, f'{name} curve {curve} at {frame}: {error}'
            for bone in u.AnimPoseExtensions.get_bone_names(old):
                actual = u.AnimPoseExtensions.get_bone_pose(new, bone, u.AnimPoseSpaces.LOCAL)
                expected = (u.Transform() if str(bone) == 'root' else
                            u.AnimPoseExtensions.get_bone_pose(old, bone, u.AnimPoseSpaces.LOCAL))
                error = max(abs(a-b) for a,b in zip(xyz(actual.translation)+xyz(actual.scale3d), xyz(expected.translation)+xyz(expected.scale3d)))
                qa,qb=actual.rotation,expected.rotation
                q1,q2=[qa.x,qa.y,qa.z,qa.w],[qb.x,qb.y,qb.z,qb.w]
                error=max(error,min(max(abs(a-b) for a,b in zip(q1,q2)),max(abs(a+b) for a,b in zip(q1,q2))))
                maximum=max(maximum,error)
                assert error < .02, f'{name} frame {frame} bone {bone}: pose error {error}'
        compressed_error=0.
        for frame in range(end-start+1):
            raw=u.AnimPoseExtensions.get_anim_pose_at_time(asset,frame/30,options())
            compressed=u.AnimPoseExtensions.get_anim_pose_at_time(asset,frame/30,options(True))
            for bone in u.AnimPoseExtensions.get_bone_names(raw):
                a=u.AnimPoseExtensions.get_bone_pose(raw,bone,u.AnimPoseSpaces.WORLD)
                b=u.AnimPoseExtensions.get_bone_pose(compressed,bone,u.AnimPoseSpaces.WORLD)
                e=max(abs(x-y) for x,y in zip(xyz(a.translation),xyz(b.translation)))
                compressed_error=max(compressed_error,e)
                assert e < .5, f'{name} compressed frame {frame} bone {bone}: {e}cm'
        results.append({'asset':asset.get_path_name(),'duration':asset.get_play_length(),
                        'source_frames':[start,end],'planned_contact_frame':hit,'planned_contact_seconds':hit/30,
                        'maximum_local_pose_error':maximum,'maximum_curve_error':curve_error,
                        'maximum_compressed_bone_position_error_cm':compressed_error,'root_identity':True,
                        'contact_and_blend_validated':False})
    return results


if __name__ == '__main__':
    report = Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemBuild/animation-verification.json'
    run_id=uuid.uuid4().hex
    report.write_text(json.dumps({'run_id':run_id,'passed':False,'status':'running'}),encoding='utf-8')
    result = verify()
    report.write_text(json.dumps({'run_id':run_id,'passed':True,'clips':result},indent=2),encoding='utf-8')
    print('StoneGolem animation pose gate passed')
