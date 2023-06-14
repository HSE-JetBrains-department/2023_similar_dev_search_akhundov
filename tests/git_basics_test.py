import unittest

from simdev.module.git.clone_stage import CloneStage
from simdev.util.pipeline import Pipeline, PipelineCache

# Sample read-only repository
TEST_REPO_URL = "https://github.com/TheSeems/HseNotebooks"


class GitBasicsTest(unittest.TestCase):
    def setUp(self):
        self.pipeline = Pipeline()
        PipelineCache.memory.clear()

    def test_public_repo(self):
        self.pipeline.append(CloneStage(repo_urls=[TEST_REPO_URL]))
        self.pipeline.run()

        clone_context = self.pipeline.get_stage_context(CloneStage)
        self.assertEqual(1, len(clone_context.repo_contexts))

        repo_context = clone_context.repo_contexts[0]
        self.assertEqual(1, len(repo_context.contributors))

        contributor_context = next(iter(repo_context.contributors.items()))[1]
        self.assertEqual("Alexey Akhundov", contributor_context.author.name)
        self.assertEqual("me@theseems.ru", contributor_context.author.email)

        # 21 current files and 1 deleted
        self.assertEqual(22, len(contributor_context.files))
        self.assertEqual(674, contributor_context.files['LICENSE'].added_lines)
        self.assertEqual(0, contributor_context.files['LICENSE'].deleted_lines)
        self.assertEqual(674, contributor_context.files['LICENSE'].changed_lines)
