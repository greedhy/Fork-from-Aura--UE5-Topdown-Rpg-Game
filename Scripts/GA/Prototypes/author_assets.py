"""Idempotent prototype authoring; preserves existing user-tuned data values."""
import json, shutil, uuid
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
RUN = ROOT / 'Saved/GAAuthoring/Prototypes' / str(uuid.uuid4())
RUN.mkdir(parents=True)
BASE = '/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
CATALOG = '/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo'
TREE = '/Game/BluePrints/UI/SpellMenu/WBP_OffensiveSpellTree'

def tag(name):
    t = u.GameplayTag(); t.import_text('(TagName="' + name + '")'); return t

def backup(path):
    src = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    if src.exists():
        dest = RUN / 'backup' / src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dest)

def save(asset):
    if isinstance(asset, u.Blueprint): u.BlueprintEditorLibrary.compile_blueprint(asset)
    assert u.EditorAssetLibrary.save_loaded_asset(asset, False), asset.get_path_name()

def data(name, cls, values):
    path = BASE + '/' + name
    fresh = not u.EditorAssetLibrary.does_asset_exist(path)
    if fresh:
        f = u.DataAssetFactory(); f.set_editor_property('data_asset_class', cls)
        asset = TOOLS.create_asset(name, BASE, cls, f)
    else:
        backup(path); asset = u.load_asset(path)
        assert isinstance(asset, cls), path
    assert asset
    if fresh or not (ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')).exists():
        for key, value in values.items(): asset.set_editor_property(key, value)
    save(asset)
    return asset

def niagara(path):
    value = u.load_asset('/Game/Assets/Effects/' + path)
    assert value, path
    return value

def make_ga(name, config):
    path = BASE + '/GA_Prototype_' + name
    if u.EditorAssetLibrary.does_asset_exist(path):
        backup(path); bp = u.load_asset(path)
    else:
        f = u.BlueprintFactory(); f.set_editor_property('parent_class', u.PrototypeAbility)
        bp = TOOLS.create_asset('GA_Prototype_' + name, BASE, u.Blueprint, f)
    cls = u.EditorAssetLibrary.load_blueprint_class(path)
    ga = u.get_default_object(cls)
    assert isinstance(ga, u.PrototypeAbility)
    ga.set_editor_property('prototype', config)
    tags = u.GameplayTagContainer(); tags.import_text('(GameplayTags=((TagName="Abilities.Prototype.' + name + '")))')
    ga.set_editor_property('ability_tags', tags)
    ga.set_editor_property('startup_input_tag', tag(''))
    ga.set_editor_property('damage_effect_class', u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage'))
    ga.set_editor_property('damage_type', config.get_editor_property('damage_type'))
    ga.set_editor_property('debuff_chance', 0.0)
    ga.set_editor_property('cost_gameplay_effect_class', None)
    ga.set_editor_property('cooldown_gameplay_effect_class', None)
    original = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Player/Ability/Fire/FireBolt/GA_FireBolt'))
    ga.set_editor_property('activation_blocked_tags', original.get_editor_property('activation_blocked_tags'))
    # Existing single-press toggle RPC activates on authority; this mode needs no cursor target data.
    if name in ('Orbit', 'Burst'): ga.set_editor_property('net_execution_policy', u.GameplayAbilityNetExecutionPolicy.SERVER_ONLY)
    save(bp)
    return cls

report = {'run_id': RUN.name, 'success': False}
try:
    fx = {
        'fire': niagara('Projectiles/FireBolt/NS_Fireball'),
        'impact': niagara('Projectiles/FireExplosion/NS_FireExplosion'),
        'beam': niagara('Shock/NS_ElectricBeam'),
        'shards': niagara('ArcaneShards/NS_ArcaneShards'),
        'ground': niagara('Combat/NS_GroundSummon'),
        'halo': niagara('Stun/NS_Halo'),
    }
    old_orbit = u.load_asset('/Game/BluePrints/AbilitySystem/Player/Ability/PassiveSpell/OrbitingFireBolt/DA_OrbitingFireBolt')
    orbit_path = BASE + '/DA_Prototype_OrbitSettings'
    if not u.EditorAssetLibrary.does_asset_exist(orbit_path):
        orbit = TOOLS.duplicate_asset('DA_Prototype_OrbitSettings', BASE, old_orbit); save(orbit)
    else: orbit = u.load_asset(orbit_path)
    defaults = {
        'Projectile': dict(display_name='Fire Shot', summary='Launch one projectile. Hit: 25 + 5/rank.', loop_vfx=fx['fire'], impact_vfx=fx['impact'], damage_type=tag('Damage.Fire'), duration=3.0),
        'Multishot': dict(display_name='Fan Shot', summary='Launch 3 projectiles in a 45-degree fan.', loop_vfx=fx['fire'], impact_vfx=fx['impact'], damage=18.0, mana_cost=15.0, cooldown=3.0, duration=3.0, damage_type=tag('Damage.Fire')),
        'Burst': dict(display_name='Arcane Burst', summary='Burst around you. Radius 300; damage 35 + 5/rank.', target_self=True, radius=300.0, damage=35.0, duration=.4, impact_vfx=fx['shards'], cooldown=4.0),
        'Beam': dict(display_name='Lightning Beam', summary='Hold to channel: 12 damage/0.5s, 3 MP/s, up to 6s.', loop_vfx=fx['beam'], damage=12.0, period=.5, mana_cost=5.0, mana_per_second=3.0, cooldown=2.0, damage_type=tag('Damage.Thunder')),
        'Surface': dict(display_name='Frost Ground', summary='Place frost ground for 6s. Slows enemies only.', radius=200.0, surface_class=u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Actor/Terrain/BP_Terrain_Frost'), cooldown=5.0, mana_cost=15.0),
        'Orbit': dict(display_name='Orbiting Bolts', summary='Toggle: 1 MP/s. Gain a bolt/3s; cap 3. Assists attacks.', mana_cost=10.0, mana_per_second=1.0, cooldown=0.0, damage=10.0, orbit_settings=orbit, damage_type=tag('Damage.Fire')),
        'Field': dict(display_name='Arcane Field', summary='Place a 6s field. Radius 250; damage 10 every 1s.', damage=10.0, loop_vfx=fx['halo'], impact_vfx=fx['ground'], cooldown=5.0, mana_cost=15.0),
        'Trap': dict(display_name='Arcane Trap', summary='Arms after 0.75s. One burst for 40 damage; lasts 12s.', damage=40.0, duration=12.0, loop_vfx=fx['halo'], impact_vfx=fx['shards'], cooldown=4.0, mana_cost=12.0),
    }
    configs, classes = {}, {}
    for name, values in defaults.items():
        values = dict(values)
        values.setdefault('damage_type', tag('Damage.Magic'))
        values['kind'] = getattr(u.AbilityPrototypeKind, name.upper())
        values['cooldown_tag'] = tag('Cooldown.Prototype.' + name)
        config = data('DA_Prototype_' + name, u.AbilityPrototype, values)
        assert config.is_valid_configuration(), name
        configs[name] = config; classes[name] = make_ga(name, config)
    # Two ready-to-use compositions; select either as a GA's Prototype to try it.
    combo = dict(defaults['Projectile'], kind=u.AbilityPrototypeKind.PROJECTILE, cooldown_tag=tag('Cooldown.Prototype.Projectile'), on_hit=configs['Field'])
    data('DA_Combo_ProjectileField', u.AbilityPrototype, combo)
    combo = dict(defaults['Trap'], kind=u.AbilityPrototypeKind.TRAP, damage_type=tag('Damage.Magic'), cooldown_tag=tag('Cooldown.Prototype.Trap'), damage=0.0, on_expire=configs['Burst'])
    data('DA_Combo_TrapBurst', u.AbilityPrototype, combo)
    for surface in ('Lava', 'Toxic', 'Vines'):
        values = dict(defaults['Surface'], kind=u.AbilityPrototypeKind.SURFACE, damage_type=tag('Damage.Magic'), cooldown_tag=tag('Cooldown.Prototype.Surface'))
        values['display_name'] = surface + ' Ground'
        values['summary'] = 'Place ' + surface.lower() + ' ground for 6s. Affects enemies only.'
        values['surface_class'] = u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Actor/Terrain/BP_Terrain_' + surface)
        data('DA_Surface_' + surface, u.AbilityPrototype, values)
    backup(CATALOG)
    catalog = u.load_asset(CATALOG)
    rows = list(catalog.get_editor_property('ability_information'))
    baseline = [r.export_text() for r in rows]
    template = next(r for r in rows if r.get_editor_property('ability_tag').export_text() == tag('Abilities.Fire.FireBolt').export_text())
    icons = dict(zip(defaults, ['FireBolt','FireBlast','ArcaneBlast','Shock','ArcaneStorm','Halo','BallLightning','ArcaneShards']))
    for name in defaults:
        identity = 'Abilities.Prototype.' + name
        matching = [i for i,r in enumerate(rows) if r.get_editor_property('ability_tag').export_text() == tag(identity).export_text()]
        assert len(matching) <= 1
        row = u.MyAbilityInfo(); row.import_text(template.export_text())
        row.import_text('(AbilityTag=(TagName="' + identity + '"),CooldownTag=(TagName="Cooldown.Prototype.' + name
            + '"),AbilityType=(TagName="Abilities.Type.Offensive"),LevelRequirement=1,Ability="/Script/Engine.BlueprintGeneratedClass\''
            + BASE + '/GA_Prototype_' + name + '.GA_Prototype_' + name + '_C\'",Icon="/Script/Engine.Texture2D\'/Game/Assets/UI/Spells/' + icons[name] + '.' + icons[name] + '\'")')
        if matching: rows[matching[0]] = row
        else: rows.append(row)
    catalog.set_editor_property('ability_information', rows); save(catalog)
    for old in baseline:
        if 'Abilities.Prototype.' not in old: assert old in [r.export_text() for r in rows], 'Existing catalog entry changed'
    backup(TREE)
    tree = u.load_asset(TREE)
    u.BlueprintEditorLibrary.reparent_blueprint(tree, u.PrototypeSpellTree)
    save(tree)
    report.update(success=True, assets={n:c.get_path_name() for n,c in configs.items()}, catalog_count=len(rows), backups=str(RUN/'backup'))
finally:
    (RUN / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    (RUN.parent / 'latest-authoring.json').write_text(json.dumps(report, indent=2), encoding='utf8')
