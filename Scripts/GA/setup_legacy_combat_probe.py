from pathlib import Path
import unreal as u
s=(Path(u.Paths.project_dir())/'Scripts/GA/setup_demon_combat_probe.py').read_text()
s=s.replace('MonsterWave1/demon-probe-restore.json','LegacyMonsterDesign/restore.json').replace('/Demon/Expansion/BP_DemonWarrior','/LegacyExpansion/BP_GoblinSpear').replace('DemonAnimationProbe','LegacyCombatProbe').replace('DemonBoundaryWall','LegacyBoundaryWall').replace('u.Vector(0,0,50)','u.Vector(0,0,51)')
exec(compile(s,'shroom_combat_setup','exec'),globals())
nav=ss.spawn_actor_from_class(u.NavMeshBoundsVolume,u.Vector(0,0,100));nav.set_actor_location(u.Vector(0,0,100),False,True);nav.set_actor_scale3d(u.Vector(12,12,3));nav.set_editor_property('tags',['LegacyCombatProbe'])
recast=ss.spawn_actor_from_class(u.RecastNavMesh,u.Vector());recast.set_editor_property('runtime_generation',u.RuntimeGenerationType.DYNAMIC)
exec((Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/unthrottle_probe.py').read_text())

source.set_editor_property('tags',['Enemy','SGCombatProbe','SGSource','GoblinSpear'])
for i,name in enumerate(['GoblinSlinger','Ghoul']):
 a=ss.spawn_actor_from_class(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/LegacyExpansion/BP_'+name),u.Vector(-700,500+i*400,100))
 a.set_actor_location(u.Vector(-700,500+i*400,100),False,True);a.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED);a.set_editor_property('tags',['Enemy','SGCombatProbe',name])
