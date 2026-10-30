import unreal as u, json
from pathlib import Path
out=Path(u.Paths.project_saved_dir())/'Equipment'
out.mkdir(exist_ok=True)
assets=u.EditorAssetLibrary.list_assets('/Game/Assets/EquipmentIcon',recursive=True,include_folder=False)
report={'icons':list(assets),'potions':{}}
cat=u.load_asset('/Game/BluePrints/DA/DA_BackpackItemDefinitions')
report['catalog']=cat.export_text() if hasattr(cat,'export_text') else str(cat.get_editor_property('items'))
for item in cat.get_editor_property('items'):
 effect=item.get_editor_property('use_effect')
 if effect:
  cdo=u.get_default_object(effect)
  report['potions'][str(item.get_editor_property('item_definition_id'))]=[m.export_text() for m in cdo.get_editor_property('modifiers')]
for path in assets[:12]:
 tex=u.load_asset(path)
 task=u.AssetExportTask();task.object=tex;task.filename=str(out/(tex.get_name()+'.tga'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.TextureExporterTGA();u.Exporter.run_asset_export_task(task)
(out/'inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

