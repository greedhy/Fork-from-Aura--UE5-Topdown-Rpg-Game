"""Read back all seven GA definitions, their graph nodes, and catalog bindings."""
import unreal as u,json,uuid
from pathlib import Path
result={'run_id':uuid.uuid4().hex,'success':False,'checks':{},'assets':{}}
def check(name,condition):
    result['checks'][name]=bool(condition);assert condition,name
def validate_graph(node,depth=0,ancestors=()):
    assert node and node.is_valid_configuration(),str(node)
    assert depth<=3 and node.get_path_name() not in ancestors,'Unbounded graph'
    for prop in ('on_hit','on_period','on_expire'):
        child=node.get_editor_property(prop)
        if child:validate_graph(child,depth+1,ancestors+(node.get_path_name(),))
try:
    catalog=u.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo')
    rows=list(catalog.get_editor_property('ability_information'))
    tags=[r.get_editor_property('ability_tag').export_text() for r in rows]
    check('unique_catalog_identities',len(tags)==len(set(tags)))
    for name in ('FireSeed','FrostFan','BrambleMine','StormSeal','Homing','Piercing','Chain'):
        combo=name in ('FireSeed','FrostFan','BrambleMine','StormSeal')
        base='/Game/BluePrints/AbilitySystem/Player/Ability/'+('Compositions/GA_' if combo else 'Prototypes/GA_Prototype_')+name
        cls=u.load_class(None,base+'.'+base.rsplit('/',1)[1]+'_C')
        assert cls,base
        ga=u.get_default_object(cls);config=ga.get_editor_property('prototype');validate_graph(config)
        identity='Abilities.'+('Composition.' if combo else 'Prototype.')+name
        matches=[r for r in rows if identity+'"' in r.get_editor_property('ability_tag').export_text()]
        check(name+'_catalog_class',len(matches)==1 and matches[0].get_editor_property('ability')==cls)
        check(name+'_unequipped',ga.get_editor_property('startup_input_tag').export_text()=='(TagName="")')
        check(name+'_cooldown_identity',config.get_editor_property('cooldown_tag').export_text()==matches[0].get_editor_property('cooldown_tag').export_text())
        result['assets'][name]={'ga':base,'config':config.get_path_name(),'kind':str(config.get_editor_property('kind'))}
    result['success']=True
except Exception as e:result['error']=repr(e)
finally:
    (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Compositions/latest-assets.json').write_text(json.dumps(result,indent=2),encoding='utf8')
