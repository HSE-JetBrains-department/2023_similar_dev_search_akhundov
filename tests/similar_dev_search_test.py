from pathlib import Path
import unittest

from simdev.module.git.repo_info_extractor import DevInfo
from simdev.module.simdev.similar_dev_searcher import SimilarDevSearcher
from simdev.util.export_utils import read_json

# String path to file containing sample dev info
# in the same format as for the repo extractor
TEST_DEV_INFO_PATH_STR = str(Path(__file__).parent / Path('data') / "dev_info.json")


class SimilarDevSearchTest(unittest.TestCase):
    def setUp(self):
        self.dev_info: DevInfo = read_json(TEST_DEV_INFO_PATH_STR)
        self.searcher = SimilarDevSearcher(self.dev_info)

    def test_len_smoke(self):
        for dev in self.dev_info:
            self.assertEqual(len(self.dev_info) - 1, len(self.searcher.search(dev)))

    def test_clone(self):
        similar = self.searcher.search('6543@obermui.de')
        self.assertAlmostEqual(1, similar['clone_1_6543@obermui.de'])
        self.assertAlmostEqual(1, similar['clone_2_6543@obermui.de'])

    def test_abs_different(self):
        similar = self.searcher.search('Maxim.Vasilev@jetbrains.com')
        self.assertAlmostEqual(0, similar['David.Pordomingo.F@gmail.com'])
        self.assertAlmostEqual(0, similar['clone_David.Pordomingo.F@gmail.com'])

    def test_limit(self):
        self.searcher = SimilarDevSearcher(self.dev_info, max_results_count=1)
        results = self.searcher.search('David.Pordomingo.F@gmail.com')
        self.assertEqual(1, len(results))
        self.assertEqual('clone_David.Pordomingo.F@gmail.com', list(results.keys())[0])
