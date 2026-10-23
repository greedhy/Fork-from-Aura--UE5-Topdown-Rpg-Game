"""Deterministic modular dungeon terrain layout. Run with host Python."""
import json
from collections import deque, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'Saved/LevelAuthoring/DungeonLabyrinth'
OUT.mkdir(parents=True, exist_ok=True)
CELL = 400
cells = {}
rooms = []

def rect(name, x0, y0, x1, y1, z=0, room=False):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            cells[x, y] = {'zone': name, 'z': z}
    if room:
        rooms.append({'name': name, 'bounds': [x0, y0, x1, y1], 'z': z})

rect('01_Entrance', 10, 0, 14, 4, room=True)
rect('02_Crossroads', 9, 7, 15, 11, room=True)
rect('03_WestCrypt', 1, 7, 5, 11, room=True)
rect('04_EastGallery', 19, 7, 23, 13, room=True)
rect('05_CentralCourt', 9, 15, 15, 20, room=True)
rect('06_UpperVault', 19, 19, 23, 23, room=True)
rect('07_RaisedSanctum', 9, 24, 15, 28, 200, room=True)
for name, bounds in [
    ('EntryPassage', (11, 5, 12, 6)), ('WestPassage', (6, 8, 8, 9)),
    ('EastPassage', (16, 8, 18, 9)), ('CentralPassage', (11, 12, 12, 14)),
    ('EastReturn', (20, 14, 21, 18)), ('CourtReturn', (16, 17, 19, 18)),
    ('WestMaze', (2, 12, 3, 16)), ('WestMaze', (4, 15, 7, 16)),
    ('WestMaze', (6, 17, 7, 25)), ('WestMaze', (2, 20, 5, 21)),
    ('WestMaze', (2, 22, 3, 25)), ('WestMaze', (4, 24, 5, 25)),
    ('MazeCourtLink', (8, 17, 8, 18)), ('BlindAlcove', (4, 13, 5, 14)),
    ('WestReliquary', (0, 23, 1, 25)),
]:
    rect('08_' + name, *bounds)
rect('09_Staircase', 11, 21, 12, 22)
rect('09_UpperLanding', 11, 23, 12, 23, 200)

start = (12, 2)
seen = {start}
queue = deque([start])
while queue:
    x, y = queue.popleft()
    for n in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
        if n in cells and n not in seen:
            seen.add(n)
            queue.append(n)
assert len(seen) == len(cells), 'Disconnected floor region'

# Pack existing 6x6 / 4x4 / 2x2 meshes without overlapping floor surfaces.
pending = {k for k, v in cells.items() if v['zone'] != '09_Staircase'}
tiles = []
while pending:
    x, y = min(pending, key=lambda v: (v[1], v[0]))
    meta = cells[x, y]
    size = next(n for n in (3, 2, 1) if all(
        (x+dx, y+dy) in pending and cells[x+dx, y+dy] == meta
        for dy in range(n) for dx in range(n)))
    tiles.append({'x': x, 'y': y, 'size': size, **meta})
    pending.difference_update((x+dx, y+dy) for dx in range(size) for dy in range(size))

edge_groups = defaultdict(list)
for (x, y), meta in cells.items():
    for neighbor, axis, line, along in [
        ((x, y-1), 'x', y, x), ((x, y+1), 'x', y+1, x),
        ((x-1, y), 'y', x, y), ((x+1, y), 'y', x+1, y),
    ]:
        if neighbor not in cells:
            edge_groups[axis, line, meta['z']].append(along)
walls = []
for (axis, line, z), values in sorted(edge_groups.items()):
    remaining = set(values)
    while remaining:
        at = min(remaining)
        count = 2 if at+1 in remaining else 1
        walls.append({'axis': axis, 'line': line, 'at': at, 'count': count, 'z': z})
        remaining.difference_update(range(at, at+count))

plan = {'level': '/Game/levels/L_DungeonLabyrinth', 'cell_cm': CELL,
        'origin_cm': [-5000, -5800], 'rooms': rooms, 'tiles': tiles, 'walls': walls,
        'cells': [{'x': x, 'y': y, **v} for (x, y), v in sorted(cells.items())],
        'reachable_cells': len(seen), 'start_cell': list(start),
        'stair': {'x': 11, 'y': 21, 'width': 800, 'run': 800, 'rise': 200, 'steps': 10},
        'intent': 'Existing dungeon kit; terrain blockout only; rooms, loops, maze branches and raised end room.'}
(OUT / 'layout.json').write_text(json.dumps(plan, indent=2), encoding='utf8')
print(json.dumps({'floor_cells': len(cells), 'packed_floor_tiles': len(tiles),
                  'wall_segments': len(walls), 'connected': len(seen) == len(cells)}))
