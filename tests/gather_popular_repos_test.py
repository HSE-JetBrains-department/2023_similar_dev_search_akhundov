import os
import unittest

from simdev.module.github.gather_popular_repos_stage import GatherPopularReposStage, PopularReposContext
from simdev.util.pipeline import Pipeline

# Repository starred by an alt account and some other guy
TEST_REPOSITORY = "TheSeems/TMoney"


class GatherPopularReposBasicTest(unittest.TestCase):
    def setUp(self):
        self.pipeline = Pipeline(saves_directory='test_saves')
        self.pipeline.remove_all_saves()

    def test_public_repository(self):
        self.pipeline.append(GatherPopularReposStage(
            PopularReposContext(source_repositories=[TEST_REPOSITORY],
                                api_tokens=[],
                                max_popular_repos_num=100,
                                page_limit=400,
                                save_filename='gather_popular_repos.json',
                                stargazers_save_directory='stargazers',
                                starred_repos_save_directory='starred')))
        self.pipeline.run()
        result = self.pipeline.get_stage_context(GatherPopularReposStage).popular_repositories
        self.assertTrue(TEST_REPOSITORY in result)
        self.assertTrue(all([stars == 1 for (repo, stars) in result.items() if repo != TEST_REPOSITORY]))
        self.assertTrue(len(result) <= 100)
