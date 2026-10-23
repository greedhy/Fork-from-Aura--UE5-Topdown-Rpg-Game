import json
from pathlib import Path
import unreal as u

def inspect():
    rows = []
    for w in u.ObjectIterator(u.MyUserWidget):
        if not w.get_world() or 'UEDPIE_' not in w.get_world().get_path_name() or 'spell' not in w.get_class().get_name().lower(): continue
        props = {}
        for name in list(dir(w)) + ['InputTag', 'SpellIconBrush', 'Cooldown Tag']:
            if any(s in name.lower() for s in ['tag', 'ability', 'icon', 'controller', 'info']):
                try: props[name] = str(w.get_editor_property(name))
                except Exception: pass
        props['images'] = [{'name': i.get_name(), 'resource': str(i.get_editor_property('brush').get_editor_property('resource_object'))} for i in u.ObjectIterator(u.Image) if i.get_path_name().startswith(w.get_path_name()+'.')]
        rows.append({'widget': w.get_path_name(), 'properties': props})
    path = Path(u.Paths.project_dir()).resolve() / 'Saved/TravelValidation/skill-bar-inspect.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding='utf8')
inspect()
