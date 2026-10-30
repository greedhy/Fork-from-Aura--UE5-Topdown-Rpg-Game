"""Create owned StoneGolem GAS/config/model assets after a full editor build."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world(), 'Stop PIE before asset authoring'
R='/Game/BluePrints/Characters/StoneGolem'
project=Path(u.Paths.project_dir()).resolve();run=uuid.uuid4().hex
output=project/'Saved/GAAuthoring/StoneGolemBuild'/run;output.mkdir()
report=project/'Saved/GAAuthoring/StoneGolemBuild/gameplay-authoring.json'
result={'run_id':run,'complete':False,'saved':[]}
report.write_text(json.dumps(result))
tools=u.AssetToolsHelpers.get_asset_tools()
owner='StoneGolemGameplayV1'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}

def ensure(name,cls,factory):
    path=R+'/'+name
    src=(project/'Content'/path.removeprefix('/Game/')).with_suffix('.uasset')
    assert path not in dirty or not src.exists(), 'Unsaved target: '+path
    if u.EditorAssetLibrary.does_asset_exist(path):
        a=u.load_asset(path)
        assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')==owner, 'Unowned target: '+path
        assert isinstance(a,cls)
        src=project/'Content'/path.removeprefix('/Game/');src=src.with_suffix('.uasset')
        if src.exists():shutil.copy2(src,output/src.name)
        return a
    a=tools.create_asset(name,R,cls,factory);assert a,path
    u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner',owner)
    return a

def save(a):
    assert u.EditorAssetLibrary.save_loaded_asset(a,False)
    result['saved'].append(a.get_path_name());report.write_text(json.dumps(result,indent=2))

material=ensure('M_SG_Warning',u.Material,u.MaterialFactoryNew())
u.MaterialEditingLibrary.delete_all_material_expressions(material)
material.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property('two_sided',True)
color=u.MaterialEditingLibrary.create_material_expression(material,u.MaterialExpressionConstant3Vector)
color.set_editor_property('constant',u.LinearColor(1.5,.005,.005,1))
alpha=u.MaterialEditingLibrary.create_material_expression(material,u.MaterialExpressionConstant)
alpha.set_editor_property('r',.45)
u.MaterialEditingLibrary.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
u.MaterialEditingLibrary.connect_material_property(alpha,'',u.MaterialProperty.MP_OPACITY)
u.MaterialEditingLibrary.recompile_material(material);save(material)

def data(name,cls):
    f=u.DataAssetFactory();f.set_editor_property('data_asset_class',cls)
    return ensure(name,cls,f)

def blueprint(name,cls):
    f=u.BlueprintFactory();f.set_editor_property('parent_class',cls)
    bp=ensure(name,u.Blueprint,f)
    assert u.BlueprintEditorLibrary.get_blueprint_parent_class(bp)==cls
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    return bp,u.get_default_object(bp.generated_class())

attacks=[]
definitions=[
 ('HeavyHammer',u.StoneGolemHeavyHammer,dict(radius=180.,damage_multiplier=1.5,cooldown=4.,animation_delay=.2,lock_time=.35,recovery_end=1.6,activation_range=230.,selection_weight=3.)),
 ('Quake',u.StoneGolemQuake,dict(radius=450.,center_offset=u.Vector(),damage_multiplier=1.,cooldown=9.,animation_delay=.7,lock_time=0.,recovery_end=2.4,activation_range=450.,selection_weight=1.)),
 ('ShieldBash',u.StoneGolemShieldBash,dict(shape=u.StoneGolemShape.SECTOR,radius=220.,angle=80.,center_offset=u.Vector(),damage_multiplier=.6,cooldown=5.,animation_delay=0.,lock_time=.2,contact_time=25/30,recovery_end=4/3,activation_range=220.,selection_weight=2.,knockback_speed=350.,exclamation=False,impact_socket='weapon_lSocket'))]
for name,cls,values in definitions:
    config=data('DA_SG_'+name,u.StoneGolemAttackConfig)
    tuning=u.StoneGolemAttackTuning()
    for key,value in values.items():tuning.set_editor_property(key,value)
    tuning.set_editor_property('montage',u.load_asset(R+'/Animations/AM_SG_'+('ShieldBash' if name=='ShieldBash' else 'Slam_Contact')))
    tuning.set_editor_property('warning_material',material)
    if u.EditorAssetLibrary.does_asset_exist(R+'/NS_SG_'+name):tuning.set_editor_property('impact_effect',u.load_asset(R+'/NS_SG_'+name))
    config.set_editor_property('tuning',tuning);save(config)
    bp,cdo=blueprint('GA_StoneGolem_'+name,cls.static_class())
    cdo.set_editor_property('attack_config',config)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp);attacks.append(bp.generated_class())

config=data('DA_StoneGolemElite',u.StoneGolemConfig)
for key,value in {
 'mesh':u.load_asset('/Game/StoneGolem/Mesh/SKM_StoneGolem'),
 'anim_class':u.EditorAssetLibrary.load_blueprint_class(R+'/Animations/ABP_SG_Elite'),
 'hammer':u.load_asset('/Game/StoneGolem/Mesh/SM_StoneGolem_Hammer'),
 'shield':u.load_asset('/Game/StoneGolem/Mesh/SM_StoneGolem_Shield'),
 'behavior':u.load_asset('/Game/BluePrints/AI/BehaviorTree/BT_EnemyBehaviorTree'),
 'base_damage':40.,'walk_speed':150.,'attacks':attacks,
 'damage_effect':u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage')
}.items():
    assert value is not None,key
    config.set_editor_property(key,value)
save(config)
bp,cdo=blueprint('BP_StoneGolemElite',u.StoneGolemCharacter.static_class())
cdo.set_editor_property('monster_config',config)
cdo.set_editor_property('ai_controller_class',u.MyAIController.static_class())
cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
bar=cdo.get_editor_property('health_bar')
bar.set_editor_property('widget_class',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/UI/ProgressBar/WBP_EnemyHealthBar'))
bar.set_editor_property('space',u.WidgetSpace.SCREEN)
bar.set_editor_property('draw_at_desired_size',True)
bar.set_editor_property('relative_location',u.Vector(0,0,130))
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
result['complete']=True;report.write_text(json.dumps(result,indent=2))

