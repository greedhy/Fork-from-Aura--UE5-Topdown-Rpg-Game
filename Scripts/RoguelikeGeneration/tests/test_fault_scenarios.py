"""Offline contracts for fault scenarios; these do not prove game behavior."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from make_run_fault_scenario import SCENARIOS, build_fault_request


def capture():
    rooms = [{'index': i, 'role': role, 'x': 2400*i, 'y': 0}
             for i, role in enumerate(('Entrance', 'Combat', 'Elite', 'Boss'))]
    return {'authority': True, 'generation': {'seed': 42, 'rooms': rooms},
            'run': {'rooms': rooms, 'connections': [{'from': i, 'to': i+1} for i in range(3)]}}


def checks(request):
    return [c for a in request['actions'] for field in ('until', 'checks') for c in a.get(field, [])]


class FaultScenarioTests(unittest.TestCase):
    def scenario(self, name, party=2):
        return build_fault_request(capture(), name, party, 'offline-'+name)

    def test_mutations_wait_for_spawn_queue_and_never_use_direct_revive(self):
        for name in SCENARIOS:
            with self.subTest(scenario=name):
                request = self.scenario(name)
                self.assertLessEqual(len(request['actions']), 256)
                self.assertEqual(request, self.scenario(name))
                for i, action in enumerate(request['actions']):
                    self.assertNotIn(action['action'], ('revive_player', 'kill_mass', 'remove_mass'))
                    if action['action'] in ('kill_actor_group', 'damage_actor', 'down_player', 'destroy_actor'):
                        previous = request['actions'][i-1]
                        self.assertEqual(previous['action'], 'wait')
                        self.assertIn({'scope':'authority', 'path':'run.pending_enemy_spawns',
                                       'op':'eq', 'value':0}, previous['until'])

    def test_clear_revival_requires_living_partner_and_both_worlds_recover(self):
        request = self.scenario('clear-revive')
        down = next(i for i, a in enumerate(request['actions']) if a['action']=='down_player')
        remaining_damage = [a for a in request['actions'][down+1:]
                            if a['action'] in ('damage_actor', 'kill_actor_group')]
        self.assertTrue(remaining_damage)
        self.assertTrue(all(a['source_player_index']==1 for a in remaining_damage))
        self.assertIn({'scope':'all', 'path':'players.*.downed', 'op':'eq', 'value':False}, checks(request))
        with self.assertRaisesRegex(ValueError, 'requires two players'):
            self.scenario('clear-revive', party=1)

    def test_party_wipe_fails_without_crediting_the_unfinished_elite(self):
        request = self.scenario('all-down')
        self.assertEqual([a['player_index'] for a in request['actions'] if a['action']=='down_player'], [0, 1])
        self.assertEqual(request['scenario']['expected_final_coins'], 15)
        self.assertIn({'scope':'all', 'path':'run.error', 'op':'eq', 'value':'AllPlayersDown'}, checks(request))

    def test_required_removal_asserts_failure_instead_of_clear_reward(self):
        request = self.scenario('required-removal')
        removed = [a for a in request['actions'] if a['action']=='destroy_actor']
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]['target'], 'first_required')
        self.assertEqual(request['scenario']['expected_final_coins'], 0)
        self.assertIn({'scope':'all', 'path':'run.error', 'op':'contains',
                       'value':'TargetRemovedWithoutKill:'}, checks(request))

    def test_retreat_cancels_gathering_and_revisit_does_not_add_reward(self):
        request = self.scenario('gathering-retreat')
        self.assertIn({'scope':'all', 'path':'run.gathering_room', 'op':'eq', 'value':-1}, checks(request))
        self.assertEqual(request['scenario']['expected_final_coins'], 15)
        self.assertEqual(sum(a['action']=='kill_actor_group' for a in request['actions']), 2)
        final = request['actions'][-1]
        self.assertEqual(final['action'], 'capture')
        self.assertIn({'scope':'all', 'path':'run.players.*.coins', 'op':'eq', 'value':15}, final['checks'])


if __name__ == '__main__':
    unittest.main()
