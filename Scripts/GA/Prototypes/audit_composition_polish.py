"""Read-only snapshot of the eight traditional GAS compositions and their VFX."""
import json, uuid
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
run = root / 'Saved/GAAuthoring/CompositionPolish' / uuid.uuid4().hex
run.mkdir(parents=True)
names = ('FireSeed','FrostFan','BrambleMine','StormSeal','Aftershock','FrostFault','RippleMine','HunterSentry')
fields = ('kind','display_name','summary','mana_cost','cooldown','damage','damage_per_level','damage_type','range','radius','inner_radius','width','duration','period','arm_delay','count','target_self','loop_vfx','impact_vfx','surface_class')
report = {'run_id':run.name,'abilities':{},'nodes':{},'success':False}
def visit(node):
    path = node.get_path_name()
    if path in report['nodes']: return
    row = {'valid':node.is_valid_configuration()}
    report['nodes'][path] = row
    for field in fields:
        value = node.get_editor_property(field)
        row[field] = (value if isinstance(value,(bool,int,float)) else
                      value.get_path_name() if isinstance(value,u.Object) else
                      value.export_text() if isinstance(value,u.GameplayTag) else str(value))
    for field in ('on_hit','on_period','on_expire'):
        child = node.get_editor_property(field)
        row[field] = child.get_path_name() if child else None
        if child: visit(child)
try:
    for name in names:
        path = '/Game/BluePrints/AbilitySystem/Player/Ability/Compositions/GA_'+name
        cls = u.EditorAssetLibrary.load_blueprint_class(path)
        ga = u.get_default_object(cls)
        assert isinstance(ga,u.PrototypeAbility), path
        node = ga.get_editor_property('prototype')
        report['abilities'][name] = {'path':path,'node':node.get_path_name(),'network':str(ga.get_editor_property('net_execution_policy'))}
        visit(node)
    report['success'] = True
finally:
    (run/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (run.parent/'latest-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

