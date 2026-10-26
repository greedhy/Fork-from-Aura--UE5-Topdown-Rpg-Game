def _inspect_menu_layout():
    import unreal as u,json,time
    from pathlib import Path
    menus=[];start=time.monotonic()
    for p in u.ObjectIterator(u.MyPlayerController):
        if 'UEDPIE_' not in p.get_path_name() or not p.get_controlled_pawn():continue
        if p.get_local_role()==u.NetRole.ROLE_AUTHORITY:
            p.get_controlled_pawn().get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_FLYING)
            p.get_controlled_pawn().set_actor_location(u.Vector(0,-5300,700),False,True)
        if not p.is_local_controller():continue
        cls=u.load_class(None,'/Game/BluePrints/UI/SpellMenu/WBP_SpellMune.WBP_SpellMune_C')
        menu=u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('Create',(p.get_world(),cls,p))
        menu.set_widget_controller(u.MyAbilitySystemLibrary.get_spell_menu_widget_controller(p.get_world()));menu.add_to_viewport();menus.append(menu)
    def tick(dt):
        if time.monotonic()-start<1:return
        try:
            rows=[]
            for t in u.ObjectIterator(u.RichTextBlock):
                if not any(t.get_path_name().startswith(m.get_path_name()+'.') for m in menus):continue
                rows.append({'name':t.get_name(),'wrap':t.get_editor_property('wrap_text_at'),'auto':t.get_editor_property('auto_wrap_text'),'size':str(u.SlateLibrary.get_local_size(t.get_cached_geometry())),'style':str(t.get_editor_property('text_style_set'))})
            (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/menu-layout.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
        finally:
            for m in menus:m.remove_from_parent()
            menus.clear();u.unregister_slate_post_tick_callback(handle)
    handle=u.register_slate_post_tick_callback(tick)
_inspect_menu_layout()

