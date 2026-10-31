from pathlib import Path
import unreal as u
s=(Path(u.Paths.project_dir())/'Scripts/GA/setup_demon_combat_probe.py').read_text()
s=s.replace('MonsterWave1/demon-probe-restore.json','ShroomDesign/restore.json').replace('/Demon/Expansion/BP_DemonWarrior','/Shroom/Expansion/BP_Shroom').replace('DemonAnimationProbe','ShroomCombatProbe').replace('DemonBoundaryWall','ShroomBoundaryWall').replace('u.Vector(0,0,50)','u.Vector(0,0,57)')
exec(compile(s,'shroom_combat_setup','exec'),globals())
nav=ss.spawn_actor_from_class(u.NavMeshBoundsVolume,u.Vector(0,0,100));nav.set_actor_location(u.Vector(0,0,100),False,True);nav.set_actor_scale3d(u.Vector(12,12,3));nav.set_editor_property('tags',['ShroomCombatProbe'])
recast=ss.spawn_actor_from_class(u.RecastNavMesh,u.Vector());recast.set_editor_property('runtime_generation',u.RuntimeGenerationType.DYNAMIC)
exec((Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/unthrottle_probe.py').read_text())
