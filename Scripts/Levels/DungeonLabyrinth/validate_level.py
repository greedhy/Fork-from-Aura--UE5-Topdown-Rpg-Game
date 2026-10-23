"""Read back the real editor world: terrain collision, seams and navigation."""
import json
import uuid
from collections import Counter
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = root/'Saved/LevelAuthoring/DungeonLabyrinth'
plan = json.loads((out/'layout.json').read_text())
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().split('.')[0] == plan['level']
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
owned = {a.get_actor_label():a for a in actors if unreal.Name('DL_Terrain') in a.tags}
failures = []
checks = Counter()
ox,oy = plan['origin_cm']
cell = plan['cell_cm']
stair = plan['stair']
cells = {(c['x'],c['y']):c for c in plan['cells']}

def trace(a,b,ignored=None):
    hit = unreal.SystemLibrary.line_trace_single(world,unreal.Vector(*a),unreal.Vector(*b),
        unreal.TraceTypeQuery.ECC_VISIBILITY,False,ignored or [],unreal.DrawDebugTrace.NONE)
    return hit.to_tuple() if hit else None

def elevation(x,y):
    c = cells[x,y]
    if c['zone'] == '09_Staircase':
        # Sampling at cell centers lands on tread 2 or 7.
        offset = (y-stair['y']+.5)*cell
        return (int(offset/(stair['run']/stair['steps']))+1)*stair['rise']/stair['steps']
    return c['z']

def position(x,y):
    return ox+(x+.5)*cell,oy+(y+.5)*cell,elevation(x,y)+1

for (x,y),c in cells.items():
    px,py,pz = position(x,y)
    hit = trace((px,py,pz+100),(px,py,pz-20))
    checks['floor_samples'] += 1
    if not hit or not hit[0] or abs(hit[4].z-pz)>2:
        failures.append({'type':'floor_collision','cell':[x,y],'expected_z':pz,'actual_z':hit[4].z if hit else None})
    for nx,ny in [(x+1,y),(x,y+1)]:
        if (nx,ny) not in cells:
            continue
        qx,qy,qz = position(nx,ny)
        height = max(pz,qz)+100
        hit = trace((px,py,height),(qx,qy,height))
        checks['open_connections'] += 1
        if hit and hit[0]:
            failures.append({'type':'blocked_connection','from':[x,y],'to':[nx,ny],'actor':hit[9].get_actor_label()})
        if c['zone']!='09_Staircase' and cells[nx,ny]['zone']!='09_Staircase' and pz==qz:
            hit = trace(((px+qx)/2,(py+qy)/2,pz+50),((px+qx)/2,(py+qy)/2,pz-20))
            checks['floor_seams'] += 1
            if not hit or not hit[0] or abs(hit[4].z-pz)>2:
                failures.append({'type':'floor_seam','from':[x,y],'to':[nx,ny]})

for i,e in enumerate(plan['walls']):
    horizontal = e['axis']=='x'
    x = ox+(e['at']+e['count']/2)*cell if horizontal else ox+e['line']*cell
    y = oy+e['line']*cell if horizontal else oy+(e['at']+e['count']/2)*cell
    dx,dy = (0,160) if horizontal else (160,0)
    # Ignore the visible wall to independently check the dedicated blocker.
    # Sample above the 200 cm staircase, still inside the 280 cm wall.
    hit = trace((x-dx,y-dy,e['z']+240),(x+dx,y+dy,e['z']+240),[owned['DL_Wall_%03d'%i]])
    checks['wall_samples'] += 1
    if not hit or not hit[0] or hit[9].get_actor_label()!='DL_WallCollision_%03d'%i:
        failures.append({'type':'wall_collision','wall':i,'actor':hit[9].get_actor_label() if hit and hit[9] else None})

for i in range(stair['steps']):
    x = ox+stair['x']*cell+stair['width']/2
    y = oy+stair['y']*cell+(i+.5)*stair['run']/stair['steps']
    z = (i+1)*stair['rise']/stair['steps']+1
    hit = trace((x,y,z+50),(x,y,z-5))
    checks['stair_treads'] += 1
    if not hit or not hit[0] or abs(hit[4].z-z)>2:
        failures.append({'type':'stair_tread','step':i})

sx,sy,sz = position(*plan['start_cell'])
routes=[]
for room in plan['rooms']:
    x0,y0,x1,y1=room['bounds']
    target=unreal.Vector(ox+(x0+x1+1)*cell/2,oy+(y0+y1+1)*cell/2,room['z']+30)
    if room['name']=='01_Entrance':
        target.y+=200 # Avoid asking for a zero-length path to the spawn itself.
    path=unreal.NavigationSystemV1.find_path_to_location_synchronously(world,unreal.Vector(sx,sy,sz+30),target)
    valid=bool(path and path.is_valid() and not path.is_partial())
    routes.append({'room':room['name'],'valid_complete_path':valid,'points':len(path.path_points) if path else 0})
    checks['room_navigation_paths']+=1
    if not valid:
        failures.append({'type':'navigation','room':room['name']})

for x,y in [(0,25),(3,24),(4,13),(6,21),(20,17)]:
    px,py,pz=position(x,y)
    path=unreal.NavigationSystemV1.find_path_to_location_synchronously(world,unreal.Vector(sx,sy,sz+30),unreal.Vector(px,py,pz+30))
    valid=bool(path and path.is_valid() and not path.is_partial())
    checks['branch_navigation_paths']+=1
    if not valid:
        failures.append({'type':'branch_navigation','cell':[x,y]})

assert len(owned)==528, 'Unexpected task actor count: '+str(len(owned))
nav=owned['DL_NavMeshBounds']
center,extent=nav.get_actor_bounds(False)
if extent.x<5000 or extent.y<6000 or extent.z<800:
    failures.append({'type':'navigation_bounds','extent':str(extent)})
result={'run_id':str(uuid.uuid4()),'level':world.get_path_name(),'owned_actor_count':len(owned),
    'checks':dict(checks),'routes':routes,'failures':failures,'passed':not failures,
    'game_mode':world.get_world_settings().get_editor_property('default_game_mode').get_path_name(),
    'dirty_content_packages':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
(out/(result['run_id']+'-validation.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
(out/'latest-validation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
unreal.log('DL_VALIDATION '+json.dumps(result))
