import unreal as u, json
from pathlib import Path
pcs = [p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]
result = {'pcs':[{'path':p.get_path_name(),'local':p.is_local_controller(),'role':str(p.get_local_role()),'pawn':str(p.get_controlled_pawn().get_actor_location())} for p in pcs],
          'project_doc':u.PlayerController.project_world_location_to_screen.__doc__,
          'mouse_doc':u.PlayerController.set_mouse_location.__doc__}
for p,row in zip(pcs,result['pcs']):
    asc=p.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
    row['mana']=asc.get_attribute_set(u.MyAttributeSet).get_editor_property('mana').export_text()
    if p.is_local_controller():
        hit=p.call_method('GetHitResultUnderCursor',(u.CollisionChannel.ECC_TARGET,False))
        row['cursor']=hit.export_text() if hit else None
    row['enemies']=[{'pos':str(e.get_actor_location()),'health':e.get_component_by_class(u.MyAbilitySystemComponent).get_attribute_set(u.MyAttributeSet).get_editor_property('health').export_text()} for e in u.GameplayStatics.get_all_actors_of_class(p.get_world(),u.EnemyCharacter)]
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/Prototypes/inspect-pie.json').write_text(json.dumps(result,indent=2))
