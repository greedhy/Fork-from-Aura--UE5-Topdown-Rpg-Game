"""Capture live Niagara effects in the disposable PIE world after render warmup."""
import unreal as u
import time,json
from pathlib import Path
_terrain_capture={'stage':'setup','start':time.monotonic()}

def _terrain_place(pawn,x,y,z):
    half=pawn.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
    pawn.teleport(u.Vector(x,y,z+half+2),u.Rotator())
    move=pawn.get_component_by_class(u.CharacterMovementComponent)
    move.stop_movement_immediately(); move.set_movement_mode(u.MovementMode.MOVE_WALKING)

def _terrain_setattr(pawn,name,value):
    attrs=pawn.get_component_by_class(u.MyAbilitySystemComponent).get_attribute_set(u.MyAttributeSet)
    data=attrs.get_editor_property(name); data.import_text(f'(BaseValue={float(value)},CurrentValue={float(value)})')
    attrs.set_editor_property(name,data)

def _terrain_capture_tick(dt):
    try:
        q=_terrain_capture
        pcs=[p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY and p.get_controlled_pawn()]
        if not pcs: return
        world=pcs[0].get_world()
        lib=u.get_default_object(u.GameplayStatics)
        def spawn(cls,loc,rot=u.Rotator()):
            transform=u.Transform(location=loc,rotation=rot)
            a=lib.call_method('BeginDeferredActorSpawnFromClass',(world,cls,transform,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            if isinstance(a,u.EnemyCharacter): a.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
            return lib.call_method('FinishSpawningActor',(a,transform,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        if q['stage']=='setup':
            for p in pcs: _terrain_place(p.get_controlled_pawn(),0,-750,0)
            for old in u.GameplayStatics.get_all_actors_of_class(world,u.SceneCapture2D):
                if old.actor_has_tag('TerrainCapture'): old.destroy_actor()
            for enemy in u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter):
                if enemy.actor_has_tag('TerrainQADummy'): enemy.destroy_actor()
            surfaces=u.GameplayStatics.get_all_actors_of_class(world,u.TerrainSurface)
            cls=u.load_class(None,'/Game/BluePrints/Characters/Goblin/BP_Goblin.BP_Goblin_C')
            for surface in surfaces:
                enemy=spawn(cls,surface.get_actor_location()+u.Vector(0,0,100))
                enemy.tags=list(enemy.tags)+[u.Name('TerrainQADummy')]
                _terrain_setattr(enemy,'max_health',1000); _terrain_setattr(enemy,'health',1000)
                _terrain_place(enemy,surface.get_actor_location().x,surface.get_actor_location().y,surface.get_actor_location().z)
            capture=spawn(u.SceneCapture2D,u.Vector(0,-1550,2100),u.Rotator(pitch=-52,yaw=90,roll=0))
            capture.tags=[u.Name('TerrainCapture')]
            comp=capture.get_component_by_class(u.SceneCaptureComponent2D)
            comp.set_editor_property('capture_every_frame',False); comp.set_editor_property('capture_on_movement',False)
            comp.set_editor_property('capture_source',u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            comp.set_editor_property('fov_angle',65.)
            target=u.RenderingLibrary.create_render_target2d(world,1800,1100,u.TextureRenderTargetFormat.RTF_RGBA8)
            comp.set_editor_property('texture_target',target)
            names=['Lava','Frost','Toxic','Vines']
            for surface in surfaces:
                kind=surface.get_editor_property('config').get_editor_property('surface_type')
                name=names[int(kind.value)]
                pos=surface.get_actor_location()
                close=spawn(u.SceneCapture2D,pos+u.Vector(0,-450,285),u.Rotator(pitch=-30,yaw=90,roll=0))
                close.tags=[u.Name('TerrainCapture'),u.Name('Close_'+name)]
                cc=close.get_component_by_class(u.SceneCaptureComponent2D)
                cc.set_editor_property('capture_every_frame',False); cc.set_editor_property('capture_on_movement',False)
                cc.set_editor_property('capture_source',u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
                cc.set_editor_property('fov_angle',45.)
                cc.set_editor_property('texture_target',u.RenderingLibrary.create_render_target2d(world,900,650,u.TextureRenderTargetFormat.RTF_RGBA8))
            q.update(stage='warmup',start=time.monotonic())
        elif q['stage']=='warmup' and time.monotonic()-q['start']>1.2:
            for capture in u.GameplayStatics.get_all_actors_of_class(world,u.SceneCapture2D):
                if capture.actor_has_tag('TerrainCapture'): capture.get_component_by_class(u.SceneCaptureComponent2D).capture_scene()
            q.update(stage='export',start=time.monotonic())
        elif q['stage']=='export' and time.monotonic()-q['start']>.1:
            root=Path(u.Paths.project_dir()).resolve()
            for capture in u.GameplayStatics.get_all_actors_of_class(world,u.SceneCapture2D):
                if not capture.actor_has_tag('TerrainCapture'): continue
                target=capture.get_component_by_class(u.SceneCaptureComponent2D).get_editor_property('texture_target')
                name=next((str(t).removeprefix('Close_')+'Close.png' for t in capture.tags if str(t).startswith('Close_')),'EffectsPreview.png')
                u.RenderingLibrary.export_render_target(world,target,str(root/'SourceArt/TerrainSurfaces'),name)
            states=[]
            for enemy in u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter):
                if enemy.actor_has_tag('TerrainQADummy'):
                    states.append({'actor':enemy.get_path_name(),'fx':[{'path':c.get_path_name(),'system':c.get_asset().get_name(),'active':c.is_active()} for c in enemy.get_components_by_class(u.NiagaraComponent) if c.get_asset() and c.get_asset().get_name().endswith('_Status')]})
            (root/'Saved/TerrainSurfaces/visual_capture.json').write_text(json.dumps(states,indent=2))
            u.unregister_slate_post_tick_callback(_terrain_capture_callback)
            u.log('TERRAIN_EFFECTS_PREVIEW_SAVED')
    except Exception as error:
        u.unregister_slate_post_tick_callback(_terrain_capture_callback)
        u.log_error('TERRAIN_CAPTURE '+repr(error))
_terrain_capture_callback=u.register_slate_post_tick_callback(_terrain_capture_tick)
