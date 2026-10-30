"""Host-side, project-bound sequential floor checks (default: 20 solo + 10 duo).

Open the saved, clean L_RoguelikeFloor host and stop PIE first. This command never
saves packages; temporary runtime seed/player/profile edits are restored finally.
Unknown MCP outcomes are recorded, never automatically resubmitted.
"""
import argparse
import json
import re
import sys
import textwrap
import time
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'skills/build-ga/scripts'))
from mcp_call import MCP, check_result

HOST = '/Game/RoguelikeGeneration/Maps/L_RoguelikeFloor'
DIRECTORY = ROOT / 'Saved/RoguelikeGeneration'


def save_json(path, data):
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


class Batch:
    def __init__(self, options):
        self.options, self.identity = options, uuid.uuid4().hex
        self.directory = DIRECTORY / 'batches' / self.identity
        self.directory.mkdir(parents=True, exist_ok=True)
        self.client = MCP(ROOT, 'RoguelikeFloor')
        self.sequence = 0
        self.started = time.monotonic()
        self.summary = {'batch_id': self.identity, 'passed': False, 'tests': [], 'comparisons': [],
                        'receipts': str(self.client.receipts), 'cleanup': {},
                        'limitations': ['Editor PIE only; no packaged or separate-process proof.',
                                        'Room types are metadata; room gameplay is not implemented.',
                                        'Movement input injection requires verify_movement.py separately.']}

    def call(self, name, arguments=None):
        request = {'name': name, 'arguments': arguments or {},
                   '_project_path': self.client.project_path, '_instance_uuid': self.client.instance_uuid,
                   'resource_locks': [{'id': 'world:current', 'mode': 'exclusive'}]}
        self.client.record('request', request)
        try:
            result = self.client.rpc('tools/call', request)
        except Exception as error:
            self.client.record('unknown', {'request': request, 'error': str(error)})
            raise RuntimeError('MCP outcome unknown; inspect receipts before retrying: ' + str(self.client.receipts)) from error
        self.client.record('submitted', result)
        check_result(result)
        job = (result.get('structuredContent') or {}).get('job_id') or result.get('job_id')
        if job:
            result = self.client.job(job, 25)
        check_result(result)
        self.client.record('result', result)
        return result

    def script(self, label, body):
        self.sequence += 1
        basename = f'{self.sequence:03d}-{label}'
        script = self.directory / (basename + '.py')
        receipt = self.directory / (basename + '.json')
        source = ('import unreal as u, builtins, json, traceback, runpy\nfrom pathlib import Path\n'
                  'def _floor_batch_operation():\n    result = {"ok": False}\n    try:\n'
                  + textwrap.indent(textwrap.dedent(body).strip(), '        ')
                  + '\n        result["ok"] = True\n    except Exception:\n'
                  '        result["error"] = traceback.format_exc()\n    finally:\n'
                  f'        Path({str(receipt)!r}).write_text(json.dumps(result, indent=2), encoding="utf-8")\n'
                  '_floor_batch_operation()\n')
        script.write_text(source, encoding='utf-8')
        self.call('console_exec', {'command': 'py "' + script.as_posix() + '"'})
        deadline = time.monotonic() + 5
        while not receipt.exists() and time.monotonic() < deadline:
            time.sleep(.1)
        if not receipt.exists():
            raise RuntimeError('No business receipt for ' + basename + '; do not resubmit blindly')
        result = json.loads(receipt.read_text(encoding='utf-8'))
        if not result.get('ok'):
            raise RuntimeError(basename + ': ' + result.get('error', 'Unknown editor script failure'))
        return result

    def status(self):
        result = self.call('pie_get_status')
        data = result.get('structuredContent') or result
        if 'state' not in data:
            raise RuntimeError('PIE status missing structured state: ' + repr(result))
        return data['state']

    def stop(self):
        state = self.status()
        if state != 'stopped':
            self.call('pie_stop')
        deadline = time.monotonic() + 20
        while self.status() != 'stopped':
            if time.monotonic() > deadline:
                raise RuntimeError('PIE did not stop; inspect editor before retrying')
            time.sleep(.5)

    def world_prelude(self):
        return f'''
assert not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(), 'Stop PIE first'
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().split('.')[0] == {HOST!r}, 'Open the new L_RoguelikeFloor host first'
actors = u.GameplayStatics.get_all_actors_of_class(world, u.DungeonGenerationRuntime)
assert len(actors) == 1, 'Expected exactly one floor runtime'
actor = actors[0]
'''

    def setup(self):
        if self.status() != 'stopped':
            raise RuntimeError('Stop PIE before starting a floor batch')
        return self.script('setup', self.world_prelude() + f'''
dirty = list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
assert not dirty, 'Save or discard existing edits before batching: ' + str([p.get_name() for p in dirty])
assert not hasattr(builtins, '_roguelike_floor_batch'), 'A previous batch needs restoration first'
profile = actor.get_editor_property('profile')
assert profile and profile.get_editor_property('generate_full_floor'), 'Full floor profile required'
builtins._roguelike_floor_batch = {{'id': {self.identity!r}, 'seed': actor.get_editor_property('seed'),
    'players': actor.get_editor_property('expected_players'), 'profile': profile}}
result.update(seed=actor.get_editor_property('seed'), players=actor.get_editor_property('expected_players'), profile=profile.get_path_name())
''')

    def configure(self, seed, players):
        body = self.world_prelude() + f'''
saved = getattr(builtins, '_roguelike_floor_batch', None)
assert saved and saved['id'] == {self.identity!r}, 'Missing batch restoration state'
actor.set_editor_property('profile', saved['profile'])
actor.set_editor_property('seed', {seed})
actor.set_editor_property('expected_players', {players})
'''
        if self.options.force_fallback:
            body += '''
source = saved['profile']
profile = u.new_object(u.DungeonGenerationProfile)
for key in ('room_spacing', 'ready_timeout', 'entrance', 'templates', 'generate_full_floor', 'floor_settings'):
    profile.set_editor_property(key, source.get_editor_property(key))
settings = profile.get_editor_property('floor_settings')
settings.set_editor_property('max_placement_attempts', 1)
settings.set_editor_property('max_search_steps_per_attempt', 1)
settings.set_editor_property('allow_fallback', True)
profile.set_editor_property('floor_settings', settings)
actor.set_editor_property('profile', profile)
'''
        self.script('configure', body)

    def restore(self):
        return self.script('restore', f'''
saved = getattr(builtins, '_roguelike_floor_batch', None)
if saved and saved['id'] == {self.identity!r}:
    assert not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(), 'Stop PIE before restoring settings'
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0] == {HOST!r}, 'Host changed; restoration state kept'
    actors = u.GameplayStatics.get_all_actors_of_class(world, u.DungeonGenerationRuntime)
    assert len(actors) == 1, 'Runtime missing; restoration state kept'
    actors[0].set_editor_property('seed', saved['seed'])
    actors[0].set_editor_property('expected_players', saved['players'])
    actors[0].set_editor_property('profile', saved['profile'])
    verification = getattr(builtins, '_roguelike_floor_verification', None)
    if verification and not verification.finished:
        verification.finish('Batch stopped before verification completed')
    result.update(restored=True, seed=saved['seed'], players=saved['players'], profile=saved['profile'].get_path_name())
    del builtins._roguelike_floor_batch
else:
    result['restored'] = False
result['dirty_packages'] = [p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())]
''')

    def wait_report(self, label):
        path = DIRECTORY / (label + '.json')
        deadline = time.monotonic() + self.options.timeout + 15
        while time.monotonic() < deadline:
            if path.exists():
                report = json.loads(path.read_text(encoding='utf-8'))
                if report.get('phase') == 'complete':
                    return path, report
            time.sleep(.25)
        raise RuntimeError('No completed verifier report before deadline: ' + str(path))

    def run(self):
        expected = self.options.single_count + self.options.duo_count
        prior, generation_ids = {}, set()
        setup_requested, pie_requested = False, False
        try:
            setup_requested = True
            self.summary['original_settings'] = self.setup()
            for players, count in ((1, self.options.single_count), (2, self.options.duo_count)):
                for seed in range(self.options.start_seed, self.options.start_seed + count):
                    label = f'floor-{self.identity[:12]}-{players}p-{seed}'
                    request = {'label': label, 'seed': seed, 'expected_players': players,
                               'expected_worlds': players, 'timeout': self.options.timeout}
                    if self.options.force_fallback:
                        request['expected_fallback'] = True
                    save_json(DIRECTORY / 'floor-request.json', request)
                    self.configure(seed, players)
                    verifier = str(ROOT / 'Scripts/RoguelikeGeneration/verify_floor.py')
                    self.script('register-verifier', f'runpy.run_path({verifier!r}, run_name="__floor_verifier__")')
                    pie_requested = True
                    self.call('pie_start', {'num_players': players, 'net_mode': 0 if players == 1 else 1, 'mode': 'viewport'})
                    path, report = self.wait_report(label)
                    item = {'seed': seed, 'players': players, 'report': str(path), 'passed': bool(report.get('passed')),
                            'elapsed_seconds': report.get('elapsed_seconds'), 'checks': len(report.get('checks', {}))}
                    self.summary['tests'].append(item)
                    assert report.get('request') == request, 'Verifier request mismatch'
                    assert report.get('passed') and report.get('checks') and all(report['checks'].values()), report.get('error', 'Verifier failed')
                    server = next(r for r in report['worlds'] if r['authority'])
                    assert server['generation_id'] not in generation_ids, 'GenerationId reused across sessions'
                    generation_ids.add(server['generation_id'])
                    signature = {key: server[key] for key in ('digest', 'rooms', 'connections', 'layout_version', 'main_path_length')}
                    if seed in prior:
                        equal = signature == prior[seed]
                        self.summary['comparisons'].append({'seed': seed, 'equal': equal, 'scope': 'solo_vs_duo'})
                        assert equal, 'Same seed changed manifest between solo and duo'
                    prior[seed] = signature
                    item.update(digest=server['digest'], generation_id=server['generation_id'], rooms=len(server['rooms']),
                                used_fallback=server['used_fallback'], generation_ms=server.get('generation_ms'))
                    self.stop()
                    pie_requested = False
                    print(f"PASS {len(self.summary['tests'])}/{expected} seed={seed} players={players} rooms={item['rooms']}", flush=True)
                    save_json(self.directory / 'summary.json', self.summary)
            self.summary['passed'] = len(self.summary['tests']) == expected
        except Exception:
            self.summary['error'] = traceback.format_exc()
        finally:
            if pie_requested:
                try:
                    self.stop()
                    self.summary['cleanup']['pie_stopped'] = True
                except Exception:
                    self.summary['cleanup']['stop_error'] = traceback.format_exc()
                    self.summary['passed'] = False
            if setup_requested:
                try:
                    self.summary['cleanup']['settings'] = self.restore()
                except Exception:
                    self.summary['cleanup']['restore_error'] = traceback.format_exc()
                    self.summary['passed'] = False
            self.summary['elapsed_seconds'] = round(time.monotonic() - self.started, 3)
            self.summary['report'] = str(self.directory / 'summary.json')
            save_json(self.directory / 'summary.json', self.summary)
            save_json(DIRECTORY / (self.options.label + '.json'), self.summary)
        print(json.dumps({'passed': self.summary['passed'], 'tests': len(self.summary['tests']),
                          'report': self.summary['report'], 'error': self.summary.get('error'),
                          'cleanup': self.summary['cleanup']}, ensure_ascii=False, indent=2))
        return 0 if self.summary['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--single-count', type=int, default=20)
    parser.add_argument('--duo-count', type=int, default=10)
    parser.add_argument('--start-seed', type=int, default=0)
    parser.add_argument('--timeout', type=float, default=90, help='Verifier timeout, 5..120 seconds per session')
    parser.add_argument('--force-fallback', action='store_true', help='Use a transient profile with a one-step search budget')
    parser.add_argument('--label', default='floor-batch-latest', help='Summary filename stem under Saved/RoguelikeGeneration')
    options = parser.parse_args()
    if min(options.single_count, options.duo_count) < 0 or options.single_count + options.duo_count <= 0:
        parser.error('Request at least one test and non-negative counts')
    if not 5 <= options.timeout <= 120 or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', options.label):
        parser.error('Timeout must be 5..120 and label a simple ASCII identifier')
    if not -(2 ** 31) <= options.start_seed < 2 ** 31 - max(options.single_count, options.duo_count):
        parser.error('Seeds must fit signed int32')
    return Batch(options).run()


if __name__ == '__main__':
    sys.exit(main())
