import unreal as u
from pathlib import Path
p=Path(u.Paths.project_saved_dir())/'Equipment'
p.joinpath('soul_table_dump.json').write_text(u.DataTableFunctionLibrary.export_data_table_to_json_string(u.load_asset('/Game/Equipment/DT_Equipment')),encoding='utf-8')
obj=u.load_asset('/Game/BluePrints/Input/IMC_PlayerContext')
p.joinpath('input_dump.txt').write_text('\n'.join(str(x.get_editor_property('action'))+' '+x.get_editor_property('key').export_text() for x in obj.get_editor_property('default_key_mappings').get_editor_property('mappings')),encoding='utf-8')
