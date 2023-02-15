import logging
import os

from git import GitCommandError
from pydriller import Repository
from tqdm import tqdm

from simdev.util.pipeline import Pipeline
from simdev.util.pipeline_exception import PipelineException
from simdev.util.stage import Stage
from simdev.util.utils import truncate


class AuthorCompound:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def __repr__(self) -> str:
        return "%s <%s>" % (self.name, self.email)

    def __hash__(self) -> int:
        return hash((self.name, self.email))

    def __eq__(self, o: object) -> bool:
        if isinstance(o, AuthorCompound):
            return (self.name, self.email) == (o.name, o.email)
        return False


class FileContext:
    def __init__(self, added_lines, deleted_lines):
        self.added_lines = added_lines
        self.deleted_lines = deleted_lines

    @property
    def changed_lines(self):
        return self.added_lines + self.deleted_lines


class ContributorContext:
    def __init__(self, author: AuthorCompound):
        self.author = author
        self.files = {}

    def __repr__(self) -> str:
        return repr(self.files)


class RepositoryContext:
    def __init__(self, url):
        self.url = url
        self.repository = None
        self.contributors = {}
        self.excluded = False

    def __eq__(self, o: object) -> bool:
        if isinstance(o, RepositoryContext):
            return self.url == o.url
        return False


class CloneContext:
    def __init__(self, repository_urls: list[str]):
        self.repositories = [RepositoryContext(url) for url in repository_urls]


def _fulfil_repository_info(repo_context: RepositoryContext):
    try:
        repo_context.repository = Repository(repo_context.url, num_workers=os.cpu_count())
        commits = tqdm(repo_context.repository.traverse_commits(), desc=repo_context.url)
        for commit in commits:
            author = AuthorCompound(commit.author.name, commit.author.email)
            for file in commit.modified_files:
                commits.set_postfix_str(
                    'Commit \'%s\', file \'%s\'' % (truncate(commit.msg.split('\n')[0]), truncate(file.filename)))
                context = repo_context.contributors.setdefault(author, ContributorContext(author))
                file_context = context.files.setdefault(file.filename, FileContext(0, 0))
                file_context.added_lines += file.added_lines
                file_context.deleted_lines += file.deleted_lines
    except GitCommandError as e:
        logging.warning('Failed to clone, skipping %s: %s ==> %s', repo_context.url,
                        '\"{0}\"'.format(' '.join(e.command)),
                        e.stderr.replace('\n', '\t'))
        repo_context.excluded = True


class CloneStage(Stage[CloneContext]):
    @property
    def name(self):
        return "Git Clone"

    def __init__(self, context: CloneContext):
        self._context = context

    def run(self, pipeline: Pipeline):
        if len(self._context.repositories) == 0:
            raise PipelineException("An empty list of repositories is provided")
        for context in self._context.repositories:
            _fulfil_repository_info(context)
        self._context.repositories = [context for context in self._context.repositories if not context.excluded]

    @property
    def context(self):
        return self._context
