"""Use UE's montage factory; verify real tracks instead of creation receipts."""
import json
from pathlib import Path
import unreal as u

ROOT='/Game/BluePrints/Characters/StoneGolem/Animations'
rows=[]
for seq_name,name in [('AS_SG_Slam','AM_SG_Slam'),('AS_SG_ShieldBash','AM_SG_ShieldBash'),('AS_SG_Slam_Contact','AM_SG_Slam_Contact')]:
    sequence=u.load_asset(ROOT+'/'+seq_name)
    path=ROOT+'/'+name
    montage=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
    assert path not in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}, 'Unsaved montage: '+path
    if not montage:
        factory=u.AnimMontageFactory()
        factory.set_editor_property('target_skeleton',sequence.get_editor_property('skeleton'))
        factory.set_editor_property('source_animation',sequence)
        montage=u.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,u.AnimMontage,factory)
        assert montage
        u.EditorAssetLibrary.set_metadata_tag(montage,'AuthoringOwner','StoneGolemMontageV1')
    assert u.EditorAssetLibrary.get_metadata_tag(montage,'AuthoringOwner')=='StoneGolemMontageV1'
    for field in ['blend_in','blend_out']:
        blend=montage.get_editor_property(field)
        blend.set_editor_property('blend_time',.15)
        montage.set_editor_property(field,blend)
    assert abs(montage.get_play_length()-sequence.get_play_length()) < 1.e-5
    tracks=montage.get_editor_property('slot_anim_tracks')
    assert len(tracks)==1
    segments=tracks[0].get_editor_property('anim_track').get_editor_property('anim_segments')
    assert len(segments)==1
    assert segments[0].get_editor_property('anim_reference')==sequence
    assert segments[0].get_editor_property('looping_count')==1
    assert u.EditorAssetLibrary.save_loaded_asset(montage,False)
    rows.append({'asset':path,'sequence':sequence.get_path_name(),'duration':montage.get_play_length(),
                 'slot':str(tracks[0].get_editor_property('slot_name')),'segments':1,'loop_count':1,'blend_seconds':.15})
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemBuild/montage-verification.json').write_text(json.dumps(rows,indent=2))
