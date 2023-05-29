import hashlib
import json
import logging
import os
import textwrap
from collections import defaultdict

from git import GitCommandError
from pydriller import Repository
from tqdm import tqdm

from simdev.util.pipeline import Pipeline, Stage, PipelineException


class AuthorCompound:
    """
    A simple structure that embodies both author's email and name
    """

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def __repr__(self) -> str:
        """
        :return: info about a contributor
        """
        return "%s <%s>" % (self.name, self.email)

    def __hash__(self) -> int:
        return int.from_bytes(hashlib.sha256(repr(self).encode('utf-8')).digest(), 'big')

    def __eq__(self, o: "AuthorCompound") -> bool:
        return (self.name, self.email) == (o.name, o.email)


class FileContext:
    """
    Context that embodies the change inside a file: added and deleted lines
    """

    def __init__(self, added_lines: int = 0, deleted_lines: int = 0):
        self.added_lines = added_lines
        self.deleted_lines = deleted_lines

    @property
    def changed_lines(self) -> int:
        return self.added_lines + self.deleted_lines


class ContributorContext:
    """
    Context that embodies the author and the set of files that are being changed by them per specific repository
    """

    def __init__(self, author: AuthorCompound):
        self.author = author
        self.files: dict[str, FileContext] = defaultdict(lambda: FileContext())

    def __repr__(self) -> str:
        """
        :return: info about changed files
        """
        return "%s: %s" % (repr(self.author), repr(self.files))


class RepositoryContext:
    """
    Context that embodies a repository alongside with their contributors' contexts and whether this repository is
    excluded from further consideration or not due to any reasons
    """

    def __init__(self, url: str):
        self.url = url
        self.contributors: dict[AuthorCompound] = {}

    def __eq__(self, o: object) -> bool:
        if isinstance(o, RepositoryContext):
            return self.url == o.url
        return False

    def __iter__(self):
        yield from {
            "url": self.url,
            "contributors": list(map(repr, self.contributors))
        }.items()

    def __repr__(self):
        return json.dumps(dict(self), ensure_ascii=False)

    def __hash__(self) -> int:
        return int.from_bytes(hashlib.sha256(repr(self).encode('utf-8')).digest(), 'big')


class CloneContext:
    """
    Context of the clone stage that embodies contexts of considered repositories
    """

    def __init__(self, repository_urls: list[str]):
        self.repositories = [RepositoryContext(url) for url in repository_urls]

    def fulfil_repository_info(self):
        """
        Fill in the info about repository (and its context)
        :return list of excluded repos
        """
        excluded_repos: set[RepositoryContext] = set()
        for repo_context in self.repositories:
            try:
                repo_context.repository = Repository(repo_context.url, num_workers=os.cpu_count())
                commits = tqdm(repo_context.repository.traverse_commits(), desc=repo_context.url)
                for commit in commits:
                    author = AuthorCompound(commit.author.name, commit.author.email)
                    for file in commit.modified_files:
                        commits.set_postfix_str(
                            'Commit \'%s\', file \'%s\'' % (
                                textwrap.shorten(commit.msg.split('\n')[0], width=40),
                                textwrap.shorten(file.filename, width=40)))
                        context = repo_context.contributors.setdefault(author, ContributorContext(author))
                        file_context = context.files[file.filename]
                        file_context.added_lines += file.added_lines
                        file_context.deleted_lines += file.deleted_lines
            except GitCommandError as e:
                logging.warning(F"Failed to clone, skipping {repo_context.url}: {' '.join(e.command)} ==> {e.stderr}")
                excluded_repos.add(repo_context)
            return excluded_repos


class CloneStage(Stage[CloneContext]):
    """
    Stage to clone git repositories and count changed files for their contributors
    """

    @property
    def name(self):
        return "Git Clone"

    def __init__(self, context: CloneContext):
        self._context = context

    def run(self, pipeline: Pipeline):
        """
        Fulfill info about repositories and exclude faulty ones
        """
        if len(self._context.repositories) == 0:
            raise PipelineException("An empty list of repositories is provided")
        excluded_contexts = self._context.fulfil_repository_info()
        self._context.repositories = [context for context in self._context.repositories
                                      if context not in excluded_contexts]

    @property
    def context(self):
        return self._context
