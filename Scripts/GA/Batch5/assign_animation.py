import unreal as u,json
from pathlib import Path
base='/Game/PrototypeExtensions/Batch5/'
bp=u.load_asset(base+'BP_ExtensionPlayer')
cdo=u.get_default_object(u.load_class(None,base+'BP_ExtensionPlayer.BP_ExtensionPlayer_C'))
anim=u.load_class(None,base+'ABP_ExtensionPlayer.ABP_ExtensionPlayer_C')
assert anim
cdo.get_component_by_class(u.SkeletalMeshComponent).set_editor_property('anim_class',anim)
u.BlueprintEditorLibrary.compile_blueprint(bp)
assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
assert u.EditorAssetLibrary.save_asset(base+'ABP_ExtensionPlayer',False)
Path(u.Paths.project_dir(),'Saved/GAAuthoring/Batch5/animation-assigned.json').write_text(json.dumps({'passed':True,'animation':anim.get_path_name()}),encoding='utf-8')
