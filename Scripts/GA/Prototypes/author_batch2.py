"""Create separate learnable compositions. Existing tuning is preserved on rerun."""
import unreal as u, json, uuid, shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
RUN=ROOT/'Saved/GAAuthoring/Compositions'/uuid.uuid4().hex
RUN.mkdir(parents=True)
BASE='/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes'
SOURCE='/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes'
CATALOG='/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo'
TOOLS=u.AssetToolsHelpers.get_asset_tools()
def tag(name):
    t=u.GameplayTag();t.import_text('(TagName="'+name+'")');return t
def save(a):
    if isinstance(a,u.Blueprint):u.BlueprintEditorLibrary.compile_blueprint(a)
    assert u.EditorAssetLibrary.save_loaded_asset(a,False),a.get_path_name()
def backup(path):
    src=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if src.exists():
        dest=RUN/'backup'/src.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
def node(name,source,**values):
    path=BASE+'/DA_Prototype_'+name
    if u.EditorAssetLibrary.does_asset_exist(path):
        a=u.load_asset(path)
    else:
        a=TOOLS.duplicate_asset('DA_Prototype_'+name,BASE,u.load_asset(SOURCE+'/DA_Prototype_'+source))
        for k,v in values.items():a.set_editor_property(k,v)
        save(a)
    assert a.is_valid_configuration(),path
    return a
def ga(name,config,source):
    path=BASE+'/GA_Prototype_'+name
    if u.EditorAssetLibrary.does_asset_exist(path):bp=u.load_asset(path)
    else:bp=TOOLS.duplicate_asset('GA_Prototype_'+name,BASE,u.load_asset(SOURCE+'/GA_Prototype_'+source))
    backup(path)
    cls=u.EditorAssetLibrary.load_blueprint_class(path);cdo=u.get_default_object(cls)
    cdo.set_editor_property('prototype',config)
    tags=u.GameplayTagContainer();tags.import_text('(GameplayTags=((TagName="Abilities.Prototype.'+name+'")))')
    cdo.set_editor_property('ability_tags',tags);cdo.set_editor_property('startup_input_tag',tag(''))
    save(bp);return cls
report={'run_id':RUN.name,'success':False}
try:
    assert json.loads((ROOT/'Saved/GAAuthoring/Compositions/stage1-gate.json').read_text())['passed']
    specs={
      'Homing':('Projectile',dict(kind=u.AbilityPrototypeKind.HOMING,display_name='Homing Bolt',mana_cost=12.0,cooldown=3.0,speed=600.0,duration=4.0,homing_turn_rate=360.0,damage=25.0)),
      'Piercing':('Projectile',dict(kind=u.AbilityPrototypeKind.PIERCING,display_name='Piercing Bolt',mana_cost=15.0,cooldown=3.0,count=3,damage_falloff=.8,damage=30.0,damage_type=tag('Damage.Magic'))),
      'Chain':('Beam',dict(kind=u.AbilityPrototypeKind.CHAIN,display_name='Chain Lightning',mana_cost=20.0,mana_per_second=0.0,cooldown=4.0,count=3,radius=450.0,period=.4,duration=3.0,damage=30.0,damage_falloff=.75)),
    }
    configs={}
    for name,(source,values) in specs.items():
        configs[name]=node(name,source,cooldown_tag=tag('Cooldown.Prototype.'+name),**values)
        ga(name,configs[name],source)
    backup(CATALOG);catalog=u.load_asset(CATALOG);rows=list(catalog.get_editor_property('ability_information'))
    old=[r.export_text() for r in rows];template=rows[0]
    for name in specs:
        identity='Abilities.Prototype.'+name
        matches=[i for i,r in enumerate(rows) if r.get_editor_property('ability_tag').export_text()==tag(identity).export_text()]
        assert len(matches)<=1
        row=u.MyAbilityInfo();row.import_text(template.export_text())
        row.import_text('(AbilityTag=(TagName="'+identity+'"),InputTag=(TagName=""),StatusTag=(TagName=""),CooldownTag=(TagName="Cooldown.Prototype.'+name+'"),AbilityType=(TagName="Abilities.Type.Offensive"),LevelRequirement=1,Ability="/Script/Engine.BlueprintGeneratedClass\''+BASE+'/GA_Prototype_'+name+'.GA_Prototype_'+name+'_C\'",Icon="/Script/Engine.Texture2D\'/Game/Assets/UI/Spells/Shock.Shock\'")')
        if matches:rows[matches[0]]=row
        else:rows.append(row)
    catalog.set_editor_property('ability_information',rows);save(catalog)
    for oldrow in old:
        if not any('Abilities.Prototype.'+n+'"' in oldrow for n in specs):assert oldrow in [r.export_text() for r in rows]
    report.update(success=True,assets={n:c.get_path_name() for n,c in configs.items()},catalog_count=len(rows))
except Exception as e:
    report['error']=repr(e);raise
finally:
    (RUN/'batch2-authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (RUN.parent/'latest-batch2-authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
