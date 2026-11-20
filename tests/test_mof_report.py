import tempfile
import unittest
from pathlib import Path

from mof_design.common import write_json
from mof_design.report import render_report


class ReportTests(unittest.TestCase):
    def test_zero_delivery_and_untrusted_text(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            write_json(task/'request.json', dict(engine='egmof', scene='<script>alert(1)</script>', target_value=5, seed=2))
            write_json(task/'scene.json', dict(target_unit='native'))
            write_json(task/'status.json', dict(reason='cancel_requested', wall_seconds=1))
            write_json(task/'candidates.json', [])
            summary = dict(task_id='example', status='cancelled', requested=2, attempted=0, accepted=0, unfilled=2)
            render_report(task, summary)
            report = (task/'REPORT.html').read_text(encoding='utf-8')
            self.assertIn('&lt;script&gt;', report)
            self.assertNotIn('<script>', report)
            self.assertIn('无候选提案记录', report)
            self.assertIn('cancel_requested', report)
            write_json(task/'candidates.json', [dict(id='C0001', status='rejected', reason='forbidden_elements', validation={})])
            summary.update(status='failed', attempted=1)
            render_report(task, summary)
            self.assertIn('forbidden_elements', (task/'REPORT.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
