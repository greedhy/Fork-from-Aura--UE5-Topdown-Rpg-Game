"""Build the actual spell menu on both local players and exercise the new page."""
import unreal as u, json, uuid
from pathlib import Path
result={'run_id':uuid.uuid4().hex,'checks':{},'success':False}
try:
    pcs=[p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.is_local_controller() and p.get_controlled_pawn()]
    assert len(pcs)==2
    for index,pc in enumerate(pcs):
        cls=u.load_class(None,'/Game/BluePrints/UI/SpellMenu/WBP_SpellMune.WBP_SpellMune_C')
        menu=u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('Create',(pc.get_world(),cls,pc))
        controller=u.MyAbilitySystemLibrary.get_spell_menu_widget_controller(pc.get_world())
        menu.set_widget_controller(controller)
        menu.add_to_viewport()
        menu.force_layout_prepass()
        trees=[w for w in u.ObjectIterator(u.PrototypeSpellTree) if w.get_path_name().startswith(menu.get_path_name()+'.')]
        assert len(trees)==1,('trees',len(trees))
        tree=trees[0]
        tree.call_method('ShowPrototypes')
        menu.force_layout_prepass()
        entries=[w for w in u.ObjectIterator(u.PrototypeSpellEntry) if w.get_path_name().startswith(tree.get_path_name()+'.')]
        catalog=u.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo')
        expected=sum(1 for r in catalog.get_editor_property('ability_information') if r.get_editor_property('ability') and isinstance(u.get_default_object(r.get_editor_property('ability')),u.PrototypeAbility))
        assert len(entries)==expected,('entries',len(entries),expected)
        assert all(any(b.get_path_name().startswith(e.get_path_name()+'.') for b in u.ObjectIterator(u.Button)) for e in entries),'Missing entry buttons'
        entries[0].call_method('Select')
        result['checks']['player_'+str(index)+'_all_catalog_entries']=True
        result['entry_count']=expected
        result['checks']['player_'+str(index)+'_controller_connected']=tree.get_editor_property('widget_controller')==controller
        menu.remove_from_parent()
    assert all(result['checks'].values())
    result['success']=True
except Exception as error:
    result['error']=repr(error)
finally:
    (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch3/latest-menu.json').write_text(json.dumps(result,indent=2))
    if 'menu' in globals() and menu: menu.remove_from_parent()
    for _qa_name in ('pcs','pc','menu','controller','trees','tree','entries','index','cls'):
        globals().pop(_qa_name,None)
