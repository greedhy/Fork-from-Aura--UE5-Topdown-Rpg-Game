"""Read-only monster import readiness inventory (no asset edits)."""
import unreal as u, json, uuid
from pathlib import Path
roots=['/Game/StoneGolem','/Game/ParagonGrux','/Game/RPGHeroSquad','/Game/BattleWizardPolyart','/Game/Assets','/Game/BluePrints/Characters']
registry=u.AssetRegistryHelpers.get_asset_registry()
result={'run_id':uuid.uuid4().hex,'assets':[],'success':False}
keep={'SkeletalMesh','Skeleton','AnimSequence','AnimMontage','AnimBlueprint','Blueprint','BehaviorTree'}
for root in roots:
    for a in registry.get_assets_by_path(root,recursive=True):
        kind=str(a.asset_class_path.asset_name)
        if kind not in keep: continue
        path=str(a.package_name)
        row={'path':path,'class':kind}
        for key in ['Skeleton','TargetSkeleton','ParentClass','NativeParentClass']:
            value=a.get_tag_value(key)
            if value: row[key]=str(value)
        if kind=='Blueprint' and any(x in path for x in ['StoneGolem/Blueprint','ParagonGrux','BluePrints/Characters']):
            try:
                cls=u.EditorAssetLibrary.load_blueprint_class(path)
                cdo=u.get_default_object(cls)
                row['gas_enemy']=isinstance(cdo,u.EnemyCharacter)
                if isinstance(cdo,u.Character):
                    mesh=cdo.get_component_by_class(u.SkeletalMeshComponent)
                    for key in ['skeletal_mesh_asset','anim_class']:
                        val=mesh.get_editor_property(key)
                        row[key]=val.get_path_name() if val else None
            except Exception as e: row['inspection_error']=str(e)
        result['assets'].append(row)
result['success']=True
dest=Path(u.Paths.project_dir())/'Saved/GAAuthoring/EnemyCandidates'/result['run_id']
dest.mkdir(parents=True)
(dest/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
(dest.parent/'latest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
