"""Temporary visual QA: show the real prototype page in both PIE windows."""
import unreal as u
def _prototype_show_menu():
    cls=u.load_class(None,'/Game/BluePrints/UI/SpellMenu/WBP_SpellMune.WBP_SpellMune_C')
    for pc in u.ObjectIterator(u.MyPlayerController):
        if 'UEDPIE_' not in pc.get_path_name() or not pc.is_local_controller() or not pc.get_controlled_pawn():continue
        menu=u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('Create',(pc.get_world(),cls,pc))
        menu.set_widget_controller(u.MyAbilitySystemLibrary.get_spell_menu_widget_controller(pc.get_world()))
        menu.add_to_viewport()
        menu.force_layout_prepass()
        for tree in u.ObjectIterator(u.PrototypeSpellTree):
            if tree.get_path_name().startswith(menu.get_path_name()+'.'):
                tree.call_method('ShowPrototypes')
                entries=[e for e in u.ObjectIterator(u.PrototypeSpellEntry) if e.get_path_name().startswith(tree.get_path_name()+'.')]
                if entries:entries[0].call_method('Select')
        menu.force_layout_prepass()
_prototype_show_menu()
