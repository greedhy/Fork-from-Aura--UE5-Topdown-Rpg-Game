"""Read-only real dungeon snapshot for the Wave 1 integration gate."""
import unreal as u,json
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and 'L_RoguelikeRun' in w.get_path_name()
d=next(iter(u.GameplayStatics.get_all_actors_of_class(w,u.DungeonRunDirector)))
r=json.loads(d.get_run_report());r['enemy_diagnostics']=[]
for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter):
 c=a.get_controller();brain=c.get_component_by_class(u.BrainComponent) if c else None
 source=a.get_editor_property('summoning_source')
 r['enemy_diagnostics'].append({'path':a.get_path_name(),'class':a.get_class().get_path_name(),'lease':a.get_dungeon_pool_lease(),'source':source.get_path_name() if source else None,'brain_running':bool(brain and brain.is_running()),'room':str(a.get_editor_property('monster_room_id'))})
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/room-snapshot.json').write_text(json.dumps(r,indent=2))
