"""Read a profile and seed, export a developer-only floor JSON and SVG/HTML.

Optional request: Saved/RoguelikeGeneration/floor-preview-request.json with seed,
profile, preview_label. Does not start PIE, create actors, or save Unreal assets.
"""
import hashlib
import html
import json
import re
import traceback
from pathlib import Path
import unreal as u

ROLES = ('Entrance', 'Combat', 'Treasure', 'Elite', 'Merchant', 'Rest', 'Boss')
COLORS = {'Entrance': '#6ee7b7', 'Combat': '#93c5fd', 'Treasure': '#facc15', 'Elite': '#fb923c',
          'Merchant': '#c4b5fd', 'Rest': '#67e8f9', 'Boss': '#f87171'}


def unpack_result(value, layout_expected=False):
    """Accept UE's bool/out tuple and bool-as-optional-out Python conventions."""
    values = value if isinstance(value, tuple) else (value,)
    layout = next((v for v in values if isinstance(v, u.DungeonLayout)), None)
    errors = [v for v in values if isinstance(v, str) and v]
    flags = [v for v in values if isinstance(v, bool)]
    success = not errors and (all(flags) if flags else value is not None)
    if layout_expected:
        success = success and layout is not None
    return success, layout, '; '.join(errors)


def serialize_layout(layout, spacing):
    rooms = []
    for item in layout.get_editor_property('rooms'):
        cell = item.get_editor_property('cell')
        role = item.get_editor_property('role')
        rooms.append({'id': str(item.get_editor_property('room_id')),
                      'role': next(name for name in ROLES if getattr(u.DungeonRoomRole, name.upper()) == role),
                      'template': str(item.get_editor_property('template_id')),
                      'cell_x': cell.x, 'cell_y': cell.y, 'x': cell.x * spacing, 'y': cell.y * spacing,
                      'yaw': item.get_editor_property('quarter_turns') * 90,
                      'main_index': item.get_editor_property('main_path_index'),
                      'branch_id': item.get_editor_property('branch_id'),
                      'persistent': item.get_editor_property('persistent')})
    return {'seed': layout.get_editor_property('seed'), 'layout_version': layout.get_editor_property('version'),
            'main_path_length': layout.get_editor_property('main_path_length'),
            'used_fallback': layout.get_editor_property('used_fallback'),
            'diversity_relaxed': layout.get_editor_property('diversity_relaxed'),
            'placement_attempts': layout.get_editor_property('placement_attempts'),
            'search_steps': layout.get_editor_property('search_steps'), 'room_spacing': spacing,
            'rooms': rooms, 'connections': [{'from': e.get_editor_property('from'), 'to': e.get_editor_property('to')}
                                          for e in layout.get_editor_property('connections')]}


def render_html(report, json_name):
    rooms, edges = report['rooms'], report['connections']
    low_x, high_x = min(r['cell_x'] for r in rooms), max(r['cell_x'] for r in rooms)
    low_y, high_y = min(r['cell_y'] for r in rooms), max(r['cell_y'] for r in rooms)
    width, height = (high_x - low_x + 1) * 140 + 80, (high_y - low_y + 1) * 120 + 80
    point = lambda room: ((room['cell_x'] - low_x) * 140 + 110, (room['cell_y'] - low_y) * 120 + 100)
    drawing = []
    for edge in edges:
        a, b = rooms[edge['from']], rooms[edge['to']]
        x1, y1 = point(a)
        x2, y2 = point(b)
        main = a['main_index'] >= 0 and b['main_index'] >= 0
        drawing.append(f'<line class="{"main" if main else "branch"}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    rows = []
    for room in rooms:
        x, y = point(room)
        role, identity = html.escape(room['role']), html.escape(room['id'])
        grouping = 'Main ' + str(room['main_index']) if room['main_index'] >= 0 else 'Branch ' + str(room['branch_id'])
        title = html.escape(f"{room['id']} | {room['template']} | {grouping} | cell ({room['cell_x']},{room['cell_y']}) | yaw {room['yaw']}")
        drawing.append(f'<g><title>{title}</title><rect x="{x-54}" y="{y-43}" width="108" height="86" rx="10" fill="{COLORS[room["role"]]}"/>'
                       f'<text x="{x}" y="{y-17}">{identity} · {role}</text><text class="small" x="{x}" y="{y+4}">{grouping}</text>'
                       f'<text class="small" x="{x}" y="{y+25}">({room["cell_x"]},{room["cell_y"]}) / {room["yaw"]}°</text></g>')
        rows.append('<tr>' + ''.join('<td>' + html.escape(str(value)) + '</td>' for value in
                    (room['id'], room['role'], grouping, room['template'], f"({room['cell_x']},{room['cell_y']})", room['yaw'])) + '</tr>')
    legend = ''.join(f'<span><i style="background:{color}"></i>{name}</span>' for name, color in COLORS.items())
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Floor seed {report['seed']}</title>
<style>body{{margin:0;background:#111827;color:#e5e7eb;font:15px system-ui}}header,section{{padding:20px 28px}}h1{{font-size:24px;margin:0 0 10px}}p{{max-width:900px;line-height:1.6}}a{{color:#93c5fd}}.legend{{display:flex;flex-wrap:wrap;gap:18px}}i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px}}.canvas{{overflow:auto;background:#0b1220;border:1px solid #374151}}svg{{display:block;max-width:none}}line{{stroke-linecap:round}}.main{{stroke:#fbbf24;stroke-width:7}}.branch{{stroke:#94a3b8;stroke-width:4;stroke-dasharray:7 5}}text{{fill:#111827;text-anchor:middle;font-size:12px;font-weight:700}}.small{{font-size:10px;font-weight:500}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:9px;border-bottom:1px solid #374151;text-align:left}}</style>
<header><h1>开发者布局预览 · Seed {report['seed']}</h1><p>算法 v{report['layout_version']} · 主线 {report['main_path_length']} 房 · 总计 {len(rooms)} 房 · 备用布局 {report['used_fallback']} · 尝试 {report['placement_attempts']} / 搜索步 {report['search_steps']}</p>
<p>此图展示全层调试信息，不是玩家探索地图。房间类型目前仅表示用途；不代表宝箱、商人或战斗玩法已接入。金色实线为主线，虚线为支路；悬停查看模板。<a href="{json_name}">JSON</a></p><div class="legend">{legend}</div>
<p>缩放 <input type="range" min="25" max="150" value="75" oninput="document.querySelector('svg').style.width=({width}*this.value/100)+'px'"></p></header>
<section class="canvas"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" style="width:{width*.75}px">{''.join(drawing)}</svg></section>
<section><table><thead><tr><th>RoomId</th><th>用途</th><th>归属</th><th>模板</th><th>网格</th><th>朝向</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section></html>'''


def main():
    directory = Path(u.Paths.project_dir()).resolve() / 'Saved/RoguelikeGeneration'
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / 'floor-preview-request.json'
    request = json.loads(request_path.read_text(encoding='utf-8-sig')) if request_path.exists() else {}
    seed = int(request.get('seed', 42))
    label = request.get('preview_label', 'floor-preview-' + str(seed))
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', label):
        raise ValueError('Invalid preview label')
    output = directory / (label + '.json')
    report = {'passed': False, 'request': request, 'developer_only': True}
    try:
        assert not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(), 'Stop PIE before pure preview'
        profile_path = request.get('profile', '/Game/RoguelikeGeneration/DA_RoguelikeFloor')
        profile = u.load_asset(profile_path)
        assert isinstance(profile, u.DungeonGenerationProfile), 'Floor profile missing'
        success, layout, error = unpack_result(u.DungeonLayoutLibrary.build_floor(profile, seed), True)
        assert success, 'BuildFloor: ' + error
        valid, _, error = unpack_result(u.DungeonLayoutLibrary.validate_floor(profile, layout))
        assert valid, 'ValidateFloor: ' + error
        report.update(serialize_layout(layout, profile.get_editor_property('room_spacing')))
        canonical = u.DungeonLayoutLibrary.canonical_layout(layout)
        report.update(profile=profile_path, canonical=canonical,
                      canonical_sha256=hashlib.sha256(canonical.encode('utf-8')).hexdigest(),
                      passed=True, error=None)
        (directory / (label + '.html')).write_text(render_html(report, output.name), encoding='utf-8')
    except Exception:
        report['error'] = traceback.format_exc()
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('DUNGEON_FLOOR_PREVIEW ' + str(output) + ' passed=' + str(report['passed']))


main()
