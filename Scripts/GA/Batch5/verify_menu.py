def _batch5_menu(spend_test=False):
    import unreal as u,json,time
    from pathlib import Path
    q={'phase':'create','started':time.monotonic(),'checks':{},'passed':False}
    menus=[]
    def finish(error=None):
        u.unregister_slate_post_tick_callback(handle)
        for menu in menus:menu.remove_from_parent()
        menus.clear()
        q.update(passed=error is None,error=error)
        (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/menu.json').write_text(json.dumps(q,indent=2),encoding='utf8')
    def tick(dt):
        try:
            if time.monotonic()-q['started']>15:raise AssertionError('Menu timeout')
            pcs=[p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.is_local_controller() and p.get_controlled_pawn()]
            if len(pcs)!=2:return
            if q['phase']=='capture':
                if time.monotonic()-q['at']<1:return
                if spend_test:
                    for pc in pcs:
                        assert pc.get_controlled_pawn().call_method('GetSpellPoints')==q['point_before'][pc.get_path_name()]-1,'Menu spending did not reach authority'
                    q['checks']['menu_spend_roundtrip_both_clients']=True
                u.SystemLibrary.execute_console_command(pcs[0].get_world(),'PureMass.QA.CaptureUI 1 Batch5_Menu')
                finish();return
            if q['phase']=='create':
                for pc in pcs:
                    cls=u.load_class(None,'/Game/BluePrints/UI/SpellMenu/WBP_SpellMune.WBP_SpellMune_C')
                    menu=u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('Create',(pc.get_world(),cls,pc))
                    menu.set_widget_controller(u.MyAbilitySystemLibrary.get_spell_menu_widget_controller(pc.get_world()))
                    menu.add_to_viewport();menus.append(menu)
                q.update(phase='check',at=time.monotonic());return
            if time.monotonic()-q['at']<1:return
            for index,menu in enumerate(menus):
                trees=[w for w in u.ObjectIterator(u.PrototypeSpellTree) if w.get_path_name().startswith(menu.get_path_name()+'.')]
                assert len(trees)==1,('tree',len(trees))
                tree=trees[0];tree.call_method('ShowPrototypes');menu.force_layout_prepass()
                entries=[w for w in u.ObjectIterator(u.PrototypeSpellEntry) if w.get_path_name().startswith(tree.get_path_name()+'.')]
                assert len(entries)==35,('entry count',len(entries))
                for entry in entries:entry.call_method('Select')
                label=str(u.load_asset('/Game/PrototypeExtensions/Batch5/DA_BrambleRepulse').get_editor_property('display_name'))
                selected=next(e for e in entries if any(t.get_path_name().startswith(e.get_path_name()+'.') and str(t.get_text())==label for t in u.ObjectIterator(u.TextBlock)))
                selected.call_method('Select');selected.get_parent().get_parent().scroll_widget_into_view(selected,False)
                assert any(t.get_path_name().startswith(menu.get_path_name()+'.') and label in str(t.get_text()) for t in u.ObjectIterator(u.RichTextBlock)),'New GA description not displayed'
                q['checks']['player_'+str(index)+'_extension_description']=True
                if spend_test:
                    pc=menu.get_owning_player();q.setdefault('point_before',{})[pc.get_path_name()]=pc.get_controlled_pawn().call_method('GetSpellPoints')
                    u.get_default_object(u.SystemLibrary).call_method('K2_SetTimer',(tree.get_editor_property('widget_controller'),'SpendPointButtonPressed',.1,False,False,0.0,0.0))
                q['checks']['player_'+str(index)+'_35_selectable_entries']=True
                assert tree.get_editor_property('widget_controller')==menu.get_editor_property('widget_controller')
                q['checks']['player_'+str(index)+'_controller']=True
            q.update(phase='capture',at=time.monotonic())
        except Exception as e:finish(repr(e))
    handle=u.register_slate_post_tick_callback(tick)
_batch5_menu()
