import unreal as u,json
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.GruxEnemyCharacter) if a.actor_has_tag('SGSource'))
asc=a.get_component_by_class(u.MyAbilitySystemComponent)
d={'asc_cancel_methods':[x for x in dir(asc) if 'cancel' in x or 'attribute' in x]}
try:d['presentation']=str(a.get_editor_property('presentation'))
except Exception as e:d['presentation_error']=str(e)
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/GruxDesign/runtime-api.json').write_text(json.dumps(d,indent=2))
