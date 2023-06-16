import unittest

from simdev.module.github.popular_repos_extractor import PopularReposExtractor
from simdev.util.pipeline import PipelineCache

# Repository starred by an alt account and some other guy
TEST_REPO = "TheSeems/TMoney"


class GatherPopularReposBasicTest(unittest.TestCase):
    def setUp(self):
        PipelineCache.memory.clear()

    def test_public_repo(self):
        extractor = PopularReposExtractor(
            source_repos=[TEST_REPO],
            api_tokens=[],
            max_popular_repos_num=100,
            page_limit=400,
            stargazers_fetch_process_count=6
        )
        extractor.run()
        self.assertTrue(TEST_REPO in extractor.popular_repos)
        self.assertTrue(
            all([stars == 1 for (repo, stars) in extractor.popular_repos.items() if
                 repo != TEST_REPO]))
        self.assertTrue(len(extractor.popular_repos) <= 100)
