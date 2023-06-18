from collections import defaultdict
import logging
import textwrap
from typing import Dict, List, TypedDict

from git import GitCommandError
from pydriller import ModifiedFile, Repository
from tqdm import tqdm

# Class for storing information about a single file: lines, variables, etc.
FileInfo = TypedDict('FileInfo', {'added_lines': int, 'deleted_lines': int})

# To keep typings inplace.
# To store information about changes of a developer in some (inside)
# repository: files, in-code identifiers, languages etc.
# files: from filename to info about the file
DevRepoInfo = TypedDict('DevRepoInfo', {'files': Dict[str, FileInfo]})

# Type that embodies information about developers:
# Developer identity (Email) -> Repository path -> Repository info
DevInfo = Dict[str, Dict[str, DevRepoInfo]]


def _handle_modified_file(file: ModifiedFile, repo_info: DevRepoInfo) -> None:
    """
    Account for a single modified file
    :param file: to handle
    :param repo_info: repo info containing info about files, langs etc.
    """
    file_info = repo_info['files'][file.filename]
    file_info['added_lines'] += file.added_lines
    file_info['deleted_lines'] += file.deleted_lines


class RepoInfoExtractor:
    """
    Class for extracting information from repositories:
    commits, files (lines, variables etc.), developers
    """

    def __init__(self, repo_urls: List[str], max_commit_count: int = 10_000):
        """
        Init information about developers and their files information
        :param repo_urls: list of URLs to GitHub repositories
        :param max_commit_count: max amount of commits to process
        """
        self.repo_urls = repo_urls
        self.max_commit_count = max_commit_count
        # Information about developers:
        # Developer identity (Email) -> Repository path -> Repository info
        self._dev_info: DevInfo = defaultdict(
            lambda: defaultdict(
                lambda: DevRepoInfo(files=defaultdict(
                    lambda: FileInfo(added_lines=0, deleted_lines=0)))))

    def extract(self) -> None:
        """
        Given the list of URLs to Git repositories to clone / fetch information about
        fulfill info about repositories and exclude faulty ones
        """
        for repo_url in self.repo_urls:
            try:
                self._handle_single_repo(repo_url)
            except GitCommandError as exception:
                logging.warning(
                    "Failed to clone, skipping %s: %s ==> %s",
                    repo_url,
                    " ".join(exception.command),
                    exception.stderr,
                )

    def _handle_single_repo(self, repo_url: str) -> None:
        """
        Fill in information for a single repository: we fetch commits,
        traverse over them and get files and information about contributors
        :param repo_url: url to clone / fetch info about
        """
        repo = Repository(repo_url)
        commits = tqdm(repo.traverse_commits(), desc=repo_url)
        for index, commit in enumerate(commits):
            if index >= self.max_commit_count:
                break
            dev_email = commit.author.email
            for file in commit.modified_files:
                commits.set_postfix_str(
                    "Commit '%s', file '%s'"
                    % (
                        textwrap.shorten(commit.msg.split("\n")[0], width=40),
                        textwrap.shorten(file.filename, width=40),
                    )
                )
                _handle_modified_file(file, self._dev_info[dev_email][repo_url])

    @property
    def dev_info(self) -> DevInfo:
        """
        :return: information about developers: dict
        Developer identity (Email) -> Repository path -> Filename
        """
        return self._dev_info
