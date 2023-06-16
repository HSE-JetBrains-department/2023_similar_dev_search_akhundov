import json
import unittest

from simdev.module.git.repo_info_extractor import RepoInfoExtractor
from simdev.util.pipeline import PipelineCache

# Sample read-only repository
TEST_REPO_URL = "https://github.com/TheSeems/HseNotebooks"


class GitBasicsTest(unittest.TestCase):
    def setUp(self):
        PipelineCache.memory.clear()

    def test_public_repo(self):
        extractor = RepoInfoExtractor()
        extractor.extract([TEST_REPO_URL])
        dev_info = extractor.dev_info
        dev = dev_info['me@theseems.ru']['https://github.com/TheSeems/HseNotebooks']
        files = dev['files']

        self.assertEqual(22, len(files))
        self.assertEqual(674, files['LICENSE']['added_lines'])
        self.assertEqual(0, files['LICENSE']['deleted_lines'])
        self.assertEqual(115, files['Alg_7_2020_tasks.ipynb']['deleted_lines'])
