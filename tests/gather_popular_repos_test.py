import unittest

from simdev.module.github.gather_popular_repos_stage import GatherPopularReposStage
from simdev.util.pipeline import Pipeline, PipelineCache

# Repository starred by an alt account and some other guy
TEST_REPOSITORY = "TheSeems/TMoney"


class GatherPopularReposBasicTest(unittest.TestCase):
    def setUp(self):
        self.pipeline = Pipeline()
        PipelineCache.memory.clear()

    def test_public_repository(self):
        self.pipeline.append(GatherPopularReposStage(
            source_repos=[TEST_REPOSITORY],
            api_tokens=[],
            max_popular_repos_num=100,
            page_limit=400,
            stargazers_fetch_process_count=6))
        self.pipeline.run()
        result = self.pipeline.get_stage_context(
            GatherPopularReposStage).popular_repositories
        self.assertTrue(TEST_REPOSITORY in result)
        self.assertTrue(all([stars == 1 for (repo, stars) in result.items() if
                             repo != TEST_REPOSITORY]))
        self.assertTrue(len(result) <= 100)
