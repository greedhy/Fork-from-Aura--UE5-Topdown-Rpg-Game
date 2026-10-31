"""Read-only baseline for the three original normal enemies; no asset writes."""
import unreal as u,json,uuid
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();folder=root/'Saved/GAAuthoring/LegacyMonsterAudit'/uuid.uuid4().hex;folder.mkdir(parents=True)
mode=u.get_default_object(u.load_class(None,'/Game/RoguelikeGeneration/Gameplay/BP_DungeonRunGameMode.BP_DungeonRunGameMode_C'))
info=mode.get_editor_property('character_class_info');defaults=info.get_editor_property('character_class_information');common=list(info.get_editor_property('common_abilities'))
profile=u.load_asset('/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay')
report={'scope':'read-only; next development scope pending','types':[]}
for entry in profile.get_editor_property('normal_roster'):
 if str(entry.get_editor_property('id')) not in ['GoblinSpear','GoblinSlinger','Ghoul']:continue
 cls=entry.get_editor_property('enemy_class')
 if not isinstance(cls,u.Class):cls=u.load_class(None,str(cls))
 cdo=u.get_default_object(cls);kind=cdo.get_editor_property('character_class');mesh=cdo.get_component_by_class(u.SkeletalMeshComponent)
 row={'id':str(entry.get_editor_property('id')),'class':cls.get_path_name(),'configured_class_grants':[g.get_path_name() for g in common+list(defaults[kind].get_editor_property('startup_abilities'))],'properties':{}}
 for key in ['attack_montage','behavior_tree','auto_possess_ai','character_class','startup_ability']:
  try:row['properties'][key]=str(cdo.get_editor_property(key))
  except Exception as e:row['properties'][key]={'unavailable':str(e)}
 for key in ['skeletal_mesh_asset','anim_class']:
  obj=mesh.get_editor_property(key);row[key]=obj.get_path_name() if obj else None
 report['types'].append(row)
report['complete']=len(report['types'])==3
(folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('LEGACY_MONSTER_AUDIT '+str(folder/'report.json'))

