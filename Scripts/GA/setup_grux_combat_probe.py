from pathlib import Path
import unreal as u
s=(Path(u.Paths.project_dir())/'Scripts/GA/setup_demon_combat_probe.py').read_text()
s=s.replace('MonsterWave1/demon-probe-restore.json','GruxDesign/combat-restore.json').replace('/Demon/Expansion/BP_DemonWarrior','/Grux/Expansion/BP_GruxBoss').replace('DemonAnimationProbe','GruxCombatProbe').replace('DemonBoundaryWall','GruxBoundaryWall').replace('u.Vector(0,0,50)','u.Vector(0,0,132)')
exec(compile(s,'setup_grux_combat','exec'),globals())
nav=ss.spawn_actor_from_class(u.NavMeshBoundsVolume,u.Vector(0,0,100))
nav.set_actor_location(u.Vector(0,0,100),False,True);nav.set_actor_scale3d(u.Vector(12,12,3))
nav.set_editor_property('tags',['GruxCombatProbe'])
recast=ss.spawn_actor_from_class(u.RecastNavMesh,u.Vector());recast.set_editor_property('runtime_generation',u.RuntimeGenerationType.DYNAMIC)
recast.set_editor_property('tags',['GruxCombatProbe'])
exec((Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/unthrottle_probe.py').read_text())
