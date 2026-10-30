"""Create dedicated cropped clips, preserving imported assets. Run in Unreal Python."""
import json
import sys
import importlib
import hashlib
import shutil
import uuid
from pathlib import Path
import unreal as u

sys.path.insert(0,str(Path(u.Paths.project_dir())/'Scripts/GA/StoneGolem'))
import verify_animations
importlib.reload(verify_animations)
from verify_animations import CLIPS, ROOT, verify, options

OWNER='StoneGolemAnimationV1'
project=Path(u.Paths.project_dir())
run_id=uuid.uuid4().hex
run_dir=project/'Saved/GAAuthoring/StoneGolemBuild'/run_id
run_dir.mkdir(parents=True)
report=project/'Saved/GAAuthoring/StoneGolemBuild/animation-authoring.json'
receipt={'run_id':run_id,'saved':False,'saved_assets':[]}
report.write_text(json.dumps(receipt),encoding='utf-8')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for name,*_ in CLIPS:
    assert ROOT+'/'+name not in dirty,'Unsaved asset changes: '+name
    file=project/'Content'/((ROOT+'/'+name).removeprefix('/Game/')+'.uasset')
    if file.exists():shutil.copy2(file,run_dir/file.name)
source_hashes={str(project/'Content/StoneGolem/Animations'/(name+'.uasset')):'' for _,name,*_ in CLIPS}
for file in source_hashes:source_hashes[file]=hashlib.sha256(Path(file).read_bytes()).hexdigest()
for name, source_name, start, end, hit in CLIPS:
    target=ROOT+'/'+name
    source='/Game/StoneGolem/Animations/'+source_name
    existing=u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else None
    if existing and u.EditorAssetLibrary.get_metadata_tag(existing,'AuthoringOwner') == OWNER:
        assert u.EditorAssetLibrary.get_metadata_tag(existing,'AuthoringOwner') == OWNER, 'Unowned asset: '+target
        assert u.EditorAssetLibrary.get_metadata_tag(existing,'SourceClip')==source
        assert u.EditorAssetLibrary.get_metadata_tag(existing,'SourceFrameRange')==f'{start}:{end}'
    elif existing:
        raise RuntimeError('Unowned asset: '+target)
    asset=existing or u.EditorAssetLibrary.duplicate_asset(source,target)
    assert asset, target
    assert isinstance(asset,u.AnimSequence)
    assert abs(u.AnimationLibrary.get_time_at_frame(u.load_asset(source),1)-1/30)<1.e-6
    controller=asset.get_editor_property('controller')
    old_frames=round(asset.get_play_length()*30)
    controller.open_bracket('StoneGolem isolated attack clip')
    try:
        original=u.load_asset(source)
        poses=[u.AnimPoseExtensions.get_anim_pose_at_time(original,f/30,options()) for f in range(start,end+1)]
        controller.set_number_of_frames(u.FrameNumber(end-start))
        # Rewrite every retained key from the source; duration alone is not crop evidence.
        for bone in u.AnimPoseExtensions.get_bone_names(poses[0]):
            keys=[u.Transform() if str(bone)=='root' else u.AnimPoseExtensions.get_bone_pose(p,bone,u.AnimPoseSpaces.LOCAL) for p in poses]
            assert controller.set_bone_track_keys(bone,[k.translation for k in keys],
                [k.rotation for k in keys],[k.scale3d for k in keys]), str(bone)
        # Preserve the source float curves at 120 Hz, shifting the retained interval to zero.
        # Independent half-frame comparisons below also test interpolation between keys.
        for curve in u.AnimPoseExtensions.get_curve_names(poses[0]):
            identifier=u.AnimationCurveIdentifier()
            identifier.set_curve_identifier(curve,u.RawCurveTrackTypes.RCT_FLOAT)
            keys=[]
            for sample in range((end-start)*4+1):
                t=sample/120
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(original,start/30+t,options())
                keys.append(u.RichCurveKey(time=t,value=u.AnimPoseExtensions.get_curve_weight(pose,curve),
                                          interp_mode=u.RichCurveInterpMode.RCIM_LINEAR))
            assert controller.set_curve_keys(identifier,keys), str(curve)
    finally:
        controller.close_bracket()
    asset.set_editor_property('enable_root_motion',False)
    asset.set_editor_property('force_root_lock',True)
    asset.set_editor_property('rate_scale',1.)
    u.EditorAssetLibrary.set_metadata_tag(asset,'AuthoringOwner',OWNER)
    u.EditorAssetLibrary.set_metadata_tag(asset,'SourceClip',source)
    u.EditorAssetLibrary.set_metadata_tag(asset,'SourceFrameRange',f'{start}:{end}')

# Validate every retained frame before saving either asset.
results=verify()
for name, *_ in CLIPS:
    assert u.EditorAssetLibrary.save_asset(ROOT+'/'+name,False)
    receipt['saved_assets'].append(ROOT+'/'+name)
    report.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in source_hashes.items())
receipt.update(saved=True,clips=results,source_hashes=source_hashes,source_files_unchanged=True)
report.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('StoneGolem dedicated animation clips saved and verified')
