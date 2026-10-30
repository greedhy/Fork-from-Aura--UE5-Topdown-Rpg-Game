"""Run with editor -ExecutePythonScript; polls real PIE, uses queued native gameplay requests."""
import unreal as u, time, json, traceback
from pathlib import Path
OUT = Path(u.Paths.project_saved_dir()) / 'Equipment'
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
assert level.load_level('/Game/RoguelikeGeneration/Maps/L_RoguelikeRun')
u.EditorPythonScripting.set_keep_python_script_alive(True)
report = {'passed':False,'steps':[]}
state = {'start':time.monotonic(),'stage':0,'next':0}
def tag(name):
    t=u.GameplayTag();t.import_text('(TagName="'+name+'")');return t
def done(error=None):
    if error:report['error']=str(error)
    (OUT/'pie_soul_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(state['callback'])
    level.editor_request_end_play()
    # Close only this dedicated validation editor, not any user editor.
    u.SystemLibrary.quit_editor()
def tick(delta):
    try:
        now=time.monotonic()
        if now-state['start']>150:raise RuntimeError('PIE probe timed out at stage '+str(state['stage']))
        if now<state['next']:return
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not world:return
        pc=u.GameplayStatics.get_player_controller(world,0)
        if not isinstance(pc,u.DungeonRunController) or not pc.get_controlled_pawn():return
        souls=list(u.GameplayStatics.get_all_actors_of_class(world,u.EquipmentSoulPickup))
        ps=pc.get_editor_property('player_state')
        equipment=ps.get_equipment_component()
        if state['stage']==0:
            if len(souls)!=8:return
            state['snapshot']=ps.export_backpack_snapshot()
            report['steps'].append('Eight replicated Soul pickups spawned in entrance')
            chosen=next(x for x in souls if 'SapphireRing' in str(x.get_editor_property('pickup').get_editor_property('item_definition_id')))
            state['item']=chosen
            state['before_ids']={x.item_instance_id.export_text() for x in state['snapshot'].slots if x.quantity>0}
            location=chosen.get_actor_location();location.z+=55
            pc.get_controlled_pawn().set_actor_location(location,False,False)
            state['stage']=1;state['next']=now+3
        elif state['stage']==1:
            label=state['item'].get_editor_property('name_widget')
            assert label.is_visible(),'Nearby equipment name should be visible'
            report['steps'].append('Nearby name prompt visible')
            u.SystemLibrary.execute_console_command(world,'Shot showui filename="'+str(OUT/'soul_world.png')+'"',pc)
            assert u.DungeonRunAutomationLibrary.queue_equipment_action(pc,'Pickup',-1,tag('Equipment.Slot.Ring.Left'))
            state['stage']=2;state['next']=now+3
        elif state['stage']==2:
            assert len(souls)==7,'Successful pickup removes exactly one Soul'
            snapshot=ps.export_backpack_snapshot()
            state['slot']=next(i for i,x in enumerate(snapshot.slots) if x.quantity>0 and x.item_instance_id.export_text() not in state['before_ids'])
            state['guid']=snapshot.slots[state['slot']].item_instance_id.export_text()
            report['steps'].append('Pickup RPC removed one Soul and added a new unique instance to inventory')
            assert u.DungeonRunAutomationLibrary.queue_equipment_action(pc,'Open',-1,tag('Equipment.Slot.Ring.Left'))
            state['stage']=3;state['next']=now+4
        elif state['stage']==3:
            panels=u.WidgetLibrary.get_all_widgets_of_class(world,u.EquipmentPanel,False)
            assert any(w.is_in_viewport() for w in panels),'Equipment panel not shown with backpack'
            bags=u.WidgetLibrary.get_all_widgets_of_class(world,u.BackpackWidget,False)
            assert any(w.is_in_viewport() for w in bags),'Backpack not shown'
            vm=next(w for w in bags if w.is_in_viewport()).get_editor_property('backpack_view_model')
            vm.select_slot(state['slot'])
            report['steps'].append('Backpack and equipment panel visible together')
            report['player_state_class']=ps.get_class().get_path_name()
            report['available_slots']=equipment.get_editor_property('available_slots').export_text()
            report['equip_tag']=tag('Equipment.Slot.Ring.Left').export_text()
            report['before_equip']=ps.export_backpack_snapshot().export_text()
            u.SystemLibrary.execute_console_command(world,'Shot showui filename="'+str(OUT/'equipment_panel.png')+'"',pc)
            assert u.DungeonRunAutomationLibrary.queue_equipment_action(pc,'Equip',state['slot'],tag('Equipment.Slot.Ring.Left'))
            state['stage']=4;state['next']=now+3
        elif state['stage']==4:
            assert any(x.item_instance_id.export_text()==state['guid'] for x in equipment.get_editor_property('slots')),'Equipment request failed'
            report['steps'].append('Picked item equipped through authoritative component')
            u.SystemLibrary.execute_console_command(world,'Shot showui filename="'+str(OUT/'equipment_panel.png')+'"',pc)
            state['stage']=41;state['next']=now+2
        elif state['stage']==41:
            assert u.DungeonRunAutomationLibrary.queue_equipment_action(pc,'Unequip',-1,tag('Equipment.Slot.Ring.Left'))
            state['stage']=5;state['next']=now+3
        elif state['stage']==5:
            assert not any(x.item_instance_id.export_text()==state['guid'] for x in equipment.get_editor_property('slots')),'Unequip failed'
            report['steps'].append('Unequip returned item to backpack')
            assert u.DungeonRunAutomationLibrary.queue_equipment_action(pc,'Close',-1,tag('Equipment.Slot.Ring.Left'))
            assert u.DungeonRunAutomationLibrary.queue_restore_equipment_snapshot(pc,state['snapshot'])
            state['stage']=6;state['next']=now+2
        elif state['stage']==6:
            assert not any(w.is_in_viewport() for w in u.WidgetLibrary.get_all_widgets_of_class(world,u.EquipmentPanel,False))
            assert ps.export_backpack_snapshot().export_text()==state['snapshot'].export_text(),'Original inventory snapshot not restored'
            report['steps'].append('Equipment panel closed with backpack; original inventory snapshot restored')
            report['passed']=True;done()
    except Exception:
        done(traceback.format_exc())
state['callback']=u.register_slate_post_tick_callback(tick)
level.editor_request_begin_play()
