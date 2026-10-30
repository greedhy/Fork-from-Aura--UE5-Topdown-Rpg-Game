import unreal as u,json
from pathlib import Path
s=u.get_default_object(u.load_class(None,'/Script/GameplayAbilities.GameplayAbilitiesDeveloperSettings'))
r={'enabled':s.get_editor_property('bAllowGameplayModEvaluationChannels'),'aliases':str(s.get_editor_property('GameplayModEvaluationChannelAliases'))}
Path(u.Paths.project_saved_dir(),'Equipment','channel_settings.json').write_text(json.dumps(r),encoding='utf-8')
