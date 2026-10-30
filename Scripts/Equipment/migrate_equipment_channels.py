"""Migrate only the three authored equipment effects; preserve their modifiers and curve data."""
import unreal as u, json, re
from pathlib import Path
report=[]
for name in ['SapphireRing','RubyRing','IronGuardChest']:
    path='/Game/Equipment/Effects/GE_Equipment_'+name
    bp=u.load_asset(path)
    cdo=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(path))
    mods=[]
    for original in cdo.get_editor_property('modifiers'):
        old=original.export_text()
        assert 'ModifierOp=AddBase' in old
        new,count=re.subn(r'EvaluationChannelSettings=\(Channel=Channel\d+\)', 'EvaluationChannelSettings=(Channel=Channel1)',old)
        assert count==1
        item=u.GameplayModifierInfo();item.import_text(new);mods.append(item)
    assert mods
    cdo.set_editor_property('modifiers',mods)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    assert all('EvaluationChannelSettings=(Channel=Channel1)' in m.export_text() for m in u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(path)).get_editor_property('modifiers'))
    assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
    report.append(path)
Path(u.Paths.project_saved_dir(),'Equipment','channel_migration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('EQUIPMENT_CHANNEL_MIGRATION_SUCCESS')
