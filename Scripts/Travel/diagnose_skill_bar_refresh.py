"""Transient diagnostic: replay the HUD snapshot and compare actual icon brushes."""
import json
from pathlib import Path
import unreal as u

def inspect():
    result=[]
    for overlay in u.ObjectIterator(u.MyUserWidget):
        if not overlay.get_world() or 'UEDPIE_' not in overlay.get_world().get_path_name() or overlay.get_class().get_name()!='WBP_Overlay_C' or not overlay.is_in_viewport(): continue
        def icons():
            return [str(i.get_editor_property('brush').get_editor_property('resource_object')) for i in u.ObjectIterator(u.Image) if i.get_name()=='Image_SpellIcon' and i.get_path_name().startswith(overlay.get_path_name()+'.')]
        wc=overlay.get_editor_property('widget_controller')
        row={'world':overlay.get_world().get_path_name(), 'before':icons()}
        wc.broadcast_initial_values()
        row['after']=icons()
        result.append(row)
    (Path(u.Paths.project_dir()).resolve()/'Saved/TravelValidation/SkillBar/manual-refresh.json').write_text(json.dumps(result,indent=2),encoding='utf8')
inspect()
