import unittest

from simdev.module.git.clone_stage import CloneStage, CloneContext
from simdev.util.pipeline import Pipeline

fixed_url = "https://github.com/TheSeems/HseNotebooks"


class GitBasicsTest(unittest.TestCase):
    def setUp(self):
        self.pipeline = Pipeline()

    def test_public_repository(self):
        self.pipeline.append(CloneStage(CloneContext(repository_urls=[fixed_url])))
        self.pipeline.run()

        clone_context = self.pipeline.get_stage_context(CloneStage)
        self.assertEqual(1, len(clone_context.repositories))

        repository_context = clone_context.repositories[0]
        self.assertEqual(1, len(repository_context.contributors))

        contributor_context = next(iter(repository_context.contributors.items()))[1]
        self.assertEqual("Alexey Akhundov", contributor_context.author.name)
        self.assertEqual("me@theseems.ru", contributor_context.author.email)

        self.assertEqual(22, len(contributor_context.files))  # 21 current files and 1 deleted
        self.assertEqual(674, contributor_context.files['LICENSE'].added_lines)
        self.assertEqual(0, contributor_context.files['LICENSE'].deleted_lines)
        self.assertEqual(674, contributor_context.files['LICENSE'].changed_lines)
