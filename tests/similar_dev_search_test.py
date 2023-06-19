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
        devs = self.searcher.search('6543@obermui.de')
        self.assertAlmostEqual(1, devs['clone_1_6543@obermui.de']['score'])
        self.assertAlmostEqual(1, devs['clone_2_6543@obermui.de']['score'])

    def test_abs_different(self):
        devs = self.searcher.search('Maxim.Vasilev@jetbrains.com')
        self.assertAlmostEqual(0, devs['David.Pordomingo.F@gmail.com']['score'])
        self.assertAlmostEqual(0, devs['clone_David.Pordomingo.F@gmail.com']['score'])

    def test_limit(self):
        self.searcher = SimilarDevSearcher(self.dev_info, max_results_count=1)
        devs = self.searcher.search('David.Pordomingo.F@gmail.com')
        self.assertEqual(1, len(devs))
        self.assertEqual('clone_David.Pordomingo.F@gmail.com', list(devs.keys())[0])

    def test_top_params(self):
        devs = self.searcher.search('David.Pordomingo.F@gmail.com')
        similar_dev = devs['6543@obermui.de']
        self.assertEqual({"expected": 77, "name": 66, "path": 58, "test": 41, "t": 28},
                         similar_dev['identifiers'])
        self.assertEqual({"Go": 1}, similar_dev['langs'])
        self.assertEqual({'https://github.com/theseems/HseNotebboks': 3,
                          'https://github.com/theseems/go-enry': 1},
                         devs['multiple@gmail.com']['repos'])
