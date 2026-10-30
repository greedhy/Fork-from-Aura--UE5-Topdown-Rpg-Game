import unreal as u,json
from pathlib import Path
paths=['/Game/BluePrints/AbilitySystem/Player/Effect/GE_SecondaryAttributes','/Game/Equipment/Effects/GE_Equipment_IronGuardChest','/Game/Equipment/Effects/GE_Equipment_SapphireRing','/Game/Equipment/Effects/GE_Equipment_RubyRing']
report={}
for path in paths:
    obj=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(path))
    report[path]={'duration':str(obj.get_editor_property('duration_policy')),'modifiers':[x.export_text() for x in obj.get_editor_property('modifiers')]}
Path(u.Paths.project_saved_dir(),'Equipment','attribute_modifier_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
