import unittest

from simdev.module.github.gather_popular_repos_stage import GatherPopularReposStage, PopularReposContext
from simdev.util.pipeline import Pipeline

fixed_repo = "TheSeems/TMoney"


class GatherPopularReposBasicTest(unittest.TestCase):
    def setUp(self):
        self.pipeline = Pipeline()

    def test_public_repository(self):
        self.pipeline.append(GatherPopularReposStage(
            PopularReposContext(source_repositories=[fixed_repo],
                                api_tokens=[],
                                max_popular_repos_num=100,
                                page_limit=400)))
        self.pipeline.run()
        result = self.pipeline.get_stage_context(GatherPopularReposStage).popular_repositories
        self.assertTrue('lucko/BungeeGuard' in result)
        self.assertTrue(all([stars == 1 for (repo, stars) in result.items()]))
        self.assertTrue(len(result) <= 100)
