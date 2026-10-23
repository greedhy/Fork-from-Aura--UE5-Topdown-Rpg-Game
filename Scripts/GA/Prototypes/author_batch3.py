"""Create separate learnable compositions. Existing tuning is preserved on rerun."""
import unreal as u, json, uuid, shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
RUN=ROOT/'Saved/GAAuthoring/Batch3'/uuid.uuid4().hex
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
    shot=node('EmitterShot','Projectile',display_name='Emitter Shot',damage=15.0,damage_per_level=3.0,mana_cost=0.0,cooldown=0.0)
    specs={
      'Cone':('Projectile',dict(kind=u.AbilityPrototypeKind.CONE,display_name='Flame Arc',target_self=False,mana_cost=12.0,cooldown=3.0,damage=35.0,radius=350.0,spread_degrees=90.0,duration=.4,loop_vfx=None)),
      'Wave':('Burst',dict(kind=u.AbilityPrototypeKind.WAVE,display_name='Arcane Wave',target_self=True,mana_cost=18.0,cooldown=4.0,damage=30.0,radius=500.0,speed=350.0,duration=3.0,loop_vfx=u.load_asset('/Game/Assets/Effects/Stun/NS_Halo'),impact_vfx=u.load_asset('/Game/Assets/Effects/Shock/NS_Sparks'))),
      'Returning':('Projectile',dict(kind=u.AbilityPrototypeKind.RETURNING,display_name='Returning Bolt',mana_cost=15.0,cooldown=4.0,damage=25.0,count=3,range=600.0,speed=600.0,duration=5.0,damage_falloff=.6)),
      'Emitter':('Burst',dict(kind=u.AbilityPrototypeKind.EMITTER,display_name='Arcane Sentry',target_self=True,mana_cost=20.0,cooldown=6.0,damage=0.0,damage_per_level=0.0,period=1.0,count=4,radius=700.0,duration=6.0,on_period=shot,loop_vfx=u.load_asset('/Game/Assets/Effects/Stun/NS_Halo'),impact_vfx=None)),
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
    (RUN/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (RUN.parent/'latest-authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
