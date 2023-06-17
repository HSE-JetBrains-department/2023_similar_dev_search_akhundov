import unittest

from simdev.module.git.repo_info_extractor import RepoInfoExtractor
from simdev.util.pipeline import PipelineCache

# Sample read-only repository
TEST_REPO_URL = "https://github.com/TheSeems/HseNotebooks"

# Forked go-enry read-only repository URL for test on language classification
TEST_LANGUAGES_REPO_URL = "https://github.com/TheSeems/go-enry"


class GitBasicsTest(unittest.TestCase):
    def setUp(self):
        PipelineCache.memory.clear()

    def test_public_repo(self):
        extractor = RepoInfoExtractor([TEST_REPO_URL])
        extractor.extract()
        dev_info = extractor.dev_info
        dev = dev_info['me@theseems.ru'][TEST_REPO_URL]
        files = dev['files']

        self.assertEqual(22, len(files))
        self.assertEqual(674, files['LICENSE']['added_lines'])
        self.assertEqual(0, files['LICENSE']['deleted_lines'])
        self.assertEqual(115, files['Alg_7_2020_tasks.ipynb']['deleted_lines'])

    def test_public_repo_languages(self):
        extractor = RepoInfoExtractor([TEST_LANGUAGES_REPO_URL])
        extractor.extract()
        repo_info = extractor.dev_info['santi@mola.io'][TEST_LANGUAGES_REPO_URL]
        langs = repo_info['langs']

        self.assertEqual({'Go': 6}, dict(langs))
        repo_info = extractor.dev_info['bzz@apache.org'][TEST_LANGUAGES_REPO_URL]
        self.assertEqual(
            {"Go": 147, "Shell": 1, "Scala": 7, "Java": 4, "Makefile": 7, "CSV": 6,
             "Text": 11, "C": 4, "Python": 8},
            dict(repo_info['langs']))

    def test_commit_limit(self):
        extractor = RepoInfoExtractor(repo_urls=[TEST_REPO_URL], max_commit_count=1)
        extractor.extract()
        dev_info = extractor.dev_info
        self.assertEqual(1, len(dev_info))

        repo_info = dev_info['me@theseems.ru'][TEST_REPO_URL]
        self.assertEqual(1, len(repo_info['files']))
        self.assertEqual('LICENSE', list(repo_info['files'].keys())[0])

    def test_public_repo_identifiers(self):
        extractor = RepoInfoExtractor([TEST_LANGUAGES_REPO_URL])
        extractor.extract()
        repo_info = extractor.dev_info['bzz@apache.org'][TEST_LANGUAGES_REPO_URL]
        identifiers = repo_info['identifiers']
        self.assertTrue(
            {'string': 4115, 'name': 2941, 'expected': 2657, 'content': 2252,
             'filename': 2078, 'test': 1974, 'err': 1867, 's': 1795, 'byte': 1573,
             'filepath': 1403, 'Join': 1275, 'language': 1073, '_': 832, 'T': 814,
             'languages': 729, 'candidates': 697, 'assert': 549, 'samplesDir': 547,
             'commit': 538, 'path': 520, 'fmt': 485
             }.items() <= dict(identifiers).items())
