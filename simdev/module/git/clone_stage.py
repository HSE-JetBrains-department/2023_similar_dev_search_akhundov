import hashlib
import json
import logging
import os
import textwrap
from collections import defaultdict, namedtuple

from git import GitCommandError
from pydriller import Repository
from tqdm import tqdm

from simdev.util.pipeline import Pipeline, PipelineException, Stage

"""
A simple structure that embodies both author's email and name
"""
AuthorCompound = namedtuple('AuthorCompound', ['name', 'email'])


class FileContext:
    """
    Context that embodies the change inside a file: added and deleted lines
    """

    def __init__(self, added_lines: int = 0, deleted_lines: int = 0):
        """
        Initialize the context with added and deleted lines within the file
        :param added_lines: number of added lines
        :param deleted_lines: number of deleted lines
        """
        self.added_lines = added_lines
        self.deleted_lines = deleted_lines

    @property
    def changed_lines(self) -> int:
        """
        Get the total number of changed lines
        :return: added lines plus deleted lines
        """
        return self.added_lines + self.deleted_lines


class ContributorContext:
    """
    Context that embodies the author and the set of files that are being changed by them per specific repository
    """

    def __init__(self, author: AuthorCompound):
        """
        Initialize the contributor context
        :param author: author for whom the context is created for: their changes
        """
        self.author = author

        # Dictionary of files for the author
        # (filename inside the repository to file context - context that embodies the change inside a file)
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
        """
        Initialize the repository context
        :param url: URL to GitHub repository
        """
        self.url = url
        # Dictionary from author id (author compound - email and name) to their contributor context - context that
        # embodies the author and the set of files that are being changed by them per specific repository
        self.contributors: dict[AuthorCompound, ContributorContext] = {}

    def fulfil(self):
        """
        Fill in information for the repository context: we fetch commits, files and information about them
        and write it to the context
        """
        repository = Repository(self.url, num_workers=os.cpu_count())
        commits = tqdm(repository.traverse_commits(), desc=self.url)
        for commit in commits:
            author = AuthorCompound(commit.author.name, commit.author.email)
            for file in commit.modified_files:
                commits.set_postfix_str(
                    'Commit \'%s\', file \'%s\'' % (
                        textwrap.shorten(commit.msg.split('\n')[0], width=40),
                        textwrap.shorten(file.filename, width=40)))
                contributor_context = self.contributors.setdefault(author, ContributorContext(author))
                file_context = contributor_context.files[file.filename]
                file_context.added_lines += file.added_lines
                file_context.deleted_lines += file.deleted_lines

    def __eq__(self, o: "RepositoryContext") -> bool:
        """
        Check if the context is equal to another
        :param o: other repository context
        :return: if the context is equal to another
        """
        return self.url == o.url

    def __iter__(self):
        """
        Make it, so we can make a dict out of the context for future serialization to JSON
        """
        yield from {
            "url": self.url,
            "contributors": list(map(repr, self.contributors))
        }.items()

    def __repr__(self):
        """
        Get string representation of the context for future hashing
        :return: json string representing the context
        """
        return json.dumps(dict(self), ensure_ascii=False)

    def __hash__(self) -> int:
        """
        Hash the context by its string representation
        :return: hash value
        """
        return int.from_bytes(hashlib.sha256(repr(self).encode('utf-8')).digest(), 'big')


class CloneContext:
    """
    Context of the clone stage that embodies contexts of considered repositories
    """

    def __init__(self, repository_urls: list[str]):
        """
        Initialize the context with a list of URLs to GitHub repositories
        :param repository_urls: list of URLs to GitHub repositories to fetch information about / to clone
        """
        self.repositories = [RepositoryContext(url) for url in repository_urls]

    def fulfil(self):
        """
        Fill in the info about repository (and its context)
        :return list of excluded repos
        """
        excluded_repos: set[RepositoryContext] = set()
        for repo_context in self.repositories:
            try:
                repo_context.fulfil()
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
        """
        :return: name of the stage
        """
        return "Git Clone"

    def __init__(self, repository_urls: list[str]):
        """
        Initialize clone stage given the list of URLs to GitHub repositories to clone / fetch information about
        :param repository_urls: list of URLs to GitHub repositories
        """
        # Context of the clone stage that embodies information of considered repositories
        self._context = CloneContext(repository_urls)

    def run(self, pipeline: Pipeline):
        """
        Fulfill info about repositories and exclude faulty ones
        :param pipeline the pipeline from which the stage is executed
        """
        if len(self._context.repositories) == 0:
            raise PipelineException("An empty list of repositories is provided")
        excluded_contexts = self._context.fulfil()
        self._context.repositories = [context for context in self._context.repositories
                                      if context not in excluded_contexts]

    @property
    def context(self):
        """
        Context of the clone stage that embodies information of considered repositories
        :return: context object of the stage
        """
        return self._context
