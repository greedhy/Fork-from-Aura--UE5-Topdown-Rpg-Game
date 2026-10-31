"""Read source summon configuration and animation event windows before adaptation."""
import unreal as u,json
from pathlib import Path
r={}
cls=u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/AbilitySystem/Enemy/Ability/GA_SummonAbility')
assert cls
c=u.get_default_object(cls)
r['summon']={k:str(c.get_editor_property(k)) for k in ['num_minions','minion_classes','min_spawn_distance','max_spawn_distance','spawn_spread']}
r['animations']=[]
for d in u.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game/Assets/Enemies/Shaman/Animations',recursive=True):
 if str(d.asset_class_path.asset_name) not in ['AnimSequence','AnimMontage']:continue
 a=d.get_asset();row={'path':str(d.package_name),'length':a.get_play_length(),'notifies':[]}
 for ev in u.AnimationLibrary.get_animation_notify_events(a):
  row['notifies'].append(str(ev))
 r['animations'].append(row)
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/shaman-combat-audit.json').write_text(json.dumps(r,indent=2))
