"""Test receipt I/O without an editor; only the unavailable Unreal module is stubbed."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('receipt_subject',Path(__file__).parents[1]/'verify_run.py')
subject=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal':types.ModuleType('unreal')}):
    spec.loader.exec_module(subject)

class ReceiptTests(unittest.TestCase):
    def test_completed_exit_is_not_rejected_as_a_map_mismatch(self):
        v=subject.RunVerification.__new__(subject.RunVerification)
        v.started=time.monotonic(); v.timeout=30; v.next_sample=0; v.last_write=0
        v.index=0; v.actions=[{'action':'interact','allow_world_exit':True}]
        step={'dispatched':True,'detail':{'interaction':'EXIT'}}
        v.step=step; v.result={}
        v.collect=Mock(return_value=[]); v.write=Mock(); v.finish=Mock()
        v.validate_pie_maps=Mock(side_effect=RuntimeError('Menu would not match gameplay map'))
        v.tick(0.1)
        v.finish.assert_called_once_with()
        v.validate_pie_maps.assert_not_called()
        self.assertEqual(step['status'],'complete')
        self.assertTrue(step['world_exit_observed'])
        self.assertEqual(v.index,1)

    def test_wrong_pie_map_fails_before_any_gameplay_action(self):
        v=subject.RunVerification.__new__(subject.RunVerification)
        v.started=time.monotonic(); v.timeout=30; v.next_sample=0; v.last_write=0
        v.expected_map='/Game/RoguelikeGeneration/Maps/L_RoguelikeRun'
        v.expected_worlds=1; v.step=None; v.index=0
        v.actions=[{'action':'move_player'}]; v.result={}
        v.collect=Mock(return_value=[]); v.write=Mock(); v.finish=Mock(); v.dispatch=Mock()
        world=Mock(get_path_name=Mock(return_value='/Temp/UEDPIE_0_Untitled_1.Untitled'))
        with patch.object(subject.u,'EditorLevelLibrary',create=True) as library:
            library.get_pie_worlds.return_value=[world]
            v.tick(0.1)
        v.finish.assert_called_once()
        self.assertIn('UnexpectedPIEMap',v.finish.call_args.args[0])
        self.assertIn('/Temp/UEDPIE_0_Untitled_1',v.finish.call_args.args[0])
        v.dispatch.assert_not_called()

    def test_map_check_accepts_both_pie_instances_and_waiting_without_worlds(self):
        expected='/Game/RoguelikeGeneration/Maps/L_RoguelikeRun'
        subject.RunVerification.validate_pie_maps([],expected)
        subject.RunVerification.validate_pie_maps([
            '/Game/RoguelikeGeneration/Maps/UEDPIE_0_L_RoguelikeRun.L_RoguelikeRun',
            '/Game/RoguelikeGeneration/Maps/UEDPIE_1_L_RoguelikeRun.L_RoguelikeRun'],expected)
        with self.assertRaisesRegex(RuntimeError,'UnexpectedPIEMap'):
            subject.RunVerification.validate_pie_maps([
                '/Game/Other/Maps/UEDPIE_0_L_RoguelikeRun.L_RoguelikeRun'],expected)

    def test_receipts_keep_state_and_timings_without_repeating_performance_history(self):
        report={'phase':'Encounter','targets':[{'path':'enemy','health':100}],
                'performance':{'pool_total':12,'pool_hits':87,'sample_count_total':800,
                               'create':{'mean_ms':2.6},'samples':[{'world_seconds':i} for i in range(600)]}}
        compact=subject.RunVerification.parse_run_report(json.dumps(report))
        self.assertEqual(compact['targets'],report['targets'])
        self.assertEqual(compact['performance']['create'],{'mean_ms':2.6})
        self.assertEqual(compact['performance']['pool_hits'],87)
        self.assertEqual(compact['performance']['sample_count_total'],800)
        self.assertNotIn('samples',compact['performance'])
        self.assertEqual(compact['receipt_omitted_performance_samples'],600)
        self.assertLess(len(json.dumps(compact)),len(json.dumps(report))/10)

    def test_failed_damage_keeps_observed_health_in_receipt(self):
        v=subject.RunVerification.__new__(subject.RunVerification)
        target=Mock()
        target.get_path_name.return_value='enemy'
        source=Mock()
        source.is_dungeon_downed.return_value=False
        v.player=Mock(return_value=Mock(get_controlled_pawn=Mock(return_value=source)))
        v.select_world=Mock(return_value={
            'snapshot':{'run':{'pending_enemy_spawns':0,
                               'targets':[{'kind':'actor','path':'enemy'}]}},
            'enemies':[target]})
        v.attributes=Mock(return_value={'health':100})
        hit={'before':{'health':100},'after_immediate':{'health':100}}
        v.gas_damage=Mock(return_value=hit)
        v.step={}
        saved=[]
        v.write=lambda: saved.append(json.loads(json.dumps(v.step)))
        with self.assertRaisesRegex(RuntimeError,'ActorGroupNotKilled'):
            v.dispatch({'action':'kill_actor_group'},[])
        self.assertEqual(saved[-1]['detail']['hits'],[hit])
        self.assertTrue(saved[-1]['dispatched'])

    def verifier(self,folder):
        v=subject.RunVerification.__new__(subject.RunVerification)
        v.directory=Path(folder); v.request_id='receipt-test'; v.started=time.monotonic()
        v.result={'request_id':v.request_id,'dispatched':True}
        return v

    def test_transient_windows_lock_preserves_durable_receipt(self):
        original=Path.replace
        attempts=[]
        def replace(path,target):
            attempts.append(str(target))
            if len(attempts)<=2:
                raise PermissionError('simulated Windows reader lock')
            return original(path,target)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[3]/"Saved/RoguelikeGeneration") as folder:
            v=self.verifier(folder)
            with patch.object(Path,'replace',replace):
                v.write()
            durable=json.loads((v.directory/'run-checks/receipt-test.json').read_text())
            mirror=json.loads((v.directory/'run-check-response.json').read_text())
            self.assertEqual(durable,mirror)
            self.assertTrue(durable['dispatched'])

    def test_persistent_lock_fails_closed_without_success_mirror(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[3]/"Saved/RoguelikeGeneration") as folder:
            v=self.verifier(folder)
            with patch.object(Path,'replace',side_effect=PermissionError('persistent lock')) as replace:
                with self.assertRaises(PermissionError): v.write()
            self.assertLessEqual(replace.call_count,5)
            self.assertFalse((v.directory/'run-check-response.json').exists())

if __name__=='__main__': unittest.main()

