import unittest
from unittest.mock import patch
from publish import publish


class PublishTest(unittest.TestCase):
    def test_no_publicar_run_ajeno_o_fallido(self):
        import json
        manifest = dict(repository='grupo/backend', sha='a'*40, run_id=1, attempt=1)
        for change in [dict(head_sha='b'*40), dict(conclusion='failure'), dict(event='pull_request'),
                       dict(path='.github/workflows/workflow-pr.yml'), dict(head_branch='develop')]:
            run = dict(head_sha='a'*40, conclusion='success', event='push',
                       path='.github/workflows/workflow-main.yml', head_branch='main')
            run.update(change)
            with patch('publish.gh', return_value=json.dumps(run)) as api:
                with self.assertRaises(ValueError): publish(manifest, '.', '.')
                self.assertEqual(api.call_count, 1)

    def test_tag_existente_no_se_mueve(self):
        import json
        manifest = dict(repository='grupo/backend', sha='a'*40, run_id=1, attempt=1, version='v1.2.3')
        run = dict(head_sha='a'*40, conclusion='success', event='push',
                   path='.github/workflows/workflow-main.yml', head_branch='main')
        with patch('publish.gh', side_effect=[json.dumps(run), '[[{"ref":"refs/tags/v1.2.3"}]]']) as api:
            with self.assertRaises(ValueError): publish(manifest, '.', '.')
            self.assertEqual(api.call_count, 2)


if __name__ == '__main__': unittest.main()
