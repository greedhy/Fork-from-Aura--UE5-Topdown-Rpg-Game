import unreal as u, json
from pathlib import Path

bp=u.load_asset('/Game/PureMass/BP_MassPlayer')
anim=u.load_asset('/Game/PureMass/ABP_MassPlayer')
anim_class=u.load_class(None,'/Game/PureMass/ABP_MassPlayer.ABP_MassPlayer_C')
assert bp and anim and anim_class
cdo=u.get_default_object(u.load_class(None,'/Game/PureMass/BP_MassPlayer.BP_MassPlayer_C'))
mesh=cdo.get_component_by_class(u.SkeletalMeshComponent)
mesh.set_editor_property('anim_class',anim_class)
u.BlueprintEditorLibrary.compile_blueprint(bp)
assert u.EditorAssetLibrary.save_loaded_asset(anim,False)
assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
assert mesh.get_editor_property('anim_class')==anim_class
Path(u.Paths.project_dir(),'Saved/PureMass/PlayerAnimation/assignment.json').write_text(json.dumps({'passed':True,'anim_class':anim_class.get_path_name()}))
