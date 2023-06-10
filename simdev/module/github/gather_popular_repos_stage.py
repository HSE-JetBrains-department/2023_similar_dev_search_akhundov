from collections import Counter
from multiprocessing import Pool
from typing import Dict, List, Set

from tqdm import tqdm

from simdev.module.github.github_api_wrapper import GithubApiWrapper
from simdev.util.pipeline import Pipeline, PipelineCache, Stage


class StargazersContext:
    """
    Context for storing info about repository's stargazers
    """

    def __init__(self, repo: str):
        """
        Initialize stargazers context
        :param repo: GitHub API repository notation
        (<user>/<repository_name> or <organization>/<repository_name>)
        """
        self.repo = repo
        # Set of GitHub stargazers (GitHub usernames) of the repo
        self.stargazers: Set[str] = set()


class StarredReposContext:
    """
    Context for storing starred repositories of a user
    """

    def __init__(self, user: str):
        """
        Initialize starred repos context
        :param user: GitHub API username of user to hold starred repos of
        """
        self.user = user
        # Set of GitHub repository notations
        # (<user>/<repository_name>, <organization>/<repository_name>)
        # starred by the user
        self.repos: Set[str] = set()


class PopularReposContext:
    """
    Context for storing info about repos that are popular among certain repo(-s')
    stargazers
    """

    def __init__(
        self,
        source_repos: List[str],
        max_popular_repos_num: int,
        page_limit: int,
        api_tokens: List[str],
        starred_repos_save_directory: str,
        stargazers_save_directory: str,
    ):
        """
        Initialize popular repositories context
        :param source_repos: list of URLs to GitHub repositories
        :param max_popular_repos_num: max number of produced (most popular) repositories
        :param page_limit: GitHub API page limit
        :param api_tokens: list of GitHub API tokens
        :param starred_repos_save_directory: path to directory to store starred repos in
        :param stargazers_save_directory: path to directory to store stargazers in
        """
        self.source_repositories = source_repos
        self.api_tokens = api_tokens
        self.max_popular_repos = max_popular_repos_num
        self.page_limit = page_limit
        self.starred_repos_save_directory = starred_repos_save_directory
        self.stargazers_save_directory = stargazers_save_directory
        # Final dictionary of popular repositories:
        # GitHub repository notation to count of common stargazers
        self.popular_repositories: Dict[str, int] = {}


class GatherPopularReposStage(Stage[PopularReposContext]):
    """
    Stage for gathering popular repositories among stargazers of source repositories
    """

    @property
    def name(self):
        """
        :return: name of the stage
        """
        return "Gather popular repositories"

    def __init__(
        self,
        source_repos: List[str],
        max_popular_repos_num: int,
        page_limit: int,
        api_tokens: List[str],
        starred_repos_save_directory: str,
        stargazers_save_directory: str,
        stargazers_fetch_process_count: int,
    ):
        """
        Initialize stage with input params
        :param source_repos: list of URLs to
        GitHub repositories
        :param max_popular_repos_num: max number of produced (most popular) repositories
        :param page_limit: GitHub API page limit
        :param api_tokens: list of GitHub API tokens
        :param starred_repos_save_directory: path to directory to store starred repos in
        :param stargazers_save_directory: path to directory to store stargazers in
        :param stargazers_fetch_process_count the number
        of processes to fetch stargazers in
        """
        self._context = PopularReposContext(
            source_repos,
            max_popular_repos_num,
            page_limit,
            api_tokens,
            starred_repos_save_directory,
            stargazers_save_directory,
        )
        self._api_wrapper = GithubApiWrapper(api_tokens=self._context.api_tokens)
        self.stargazers_fetch_process_count = stargazers_fetch_process_count

        # Cache the main fetching function
        self._count_top_repos = PipelineCache.memory.cache(self._count_top_repos)

    def run(self, pipeline: Pipeline):
        """
        First of all, we fetch all the stargazers for requested
        repositories (merge them not to include duplicates).
        Then we run over all the stargazers and fetch their
        starred repositories (saving intermediate results if
        possible). After that we accumulate all the results and
        determine top-n repositories starred by initial
        stargazers.
        :param pipeline: pipline inside which the stage is run
        """
        self._context.popular_repositories = self._count_top_repos()

    def _count_top_repos(self):
        """
        Firstly, we retrieve all the stargazers for the requested repositories,
        merging them to avoid duplicates.
        Next, we iterate through each stargazer and fetch their
        starred repositories, saving intermediate results
        whenever feasible.
        Then, we gather all the results and identify the top-n
        repositories that have been starred
        by the original stargazers
        :return: The list of top-n repositories, ranked by
        the number of stars received from the initial stargazers
        """
        source_tqdm = tqdm(
            self._context.source_repositories,
            desc="Coursing through source repositories",
        )
        repo_star_counter = Counter()

        # Acknowledged stargazers maintained to avoid duplicates between several
        # source repositories
        acked_stargazers: Set[str] = set()

        for source_repo in source_tqdm:
            stargazers_context = StargazersContext(repo=source_repo)
            stargazers_context.stargazers = self._api_wrapper.fetch_stargazers(
                repo=source_repo,
                progress=source_tqdm,
                page_limit=self._context.page_limit,
            )

            selection = stargazers_context.stargazers - acked_stargazers
            with Pool(processes=self.stargazers_fetch_process_count) as pool:
                starred_repos_progress = tqdm(
                    pool.imap(self._process_stargazer, selection),
                    total=len(selection),
                    desc=f"Get starred repos for stargazers of {source_repo}",
                )

                for stargazer, starred_repos in starred_repos_progress:
                    for repo in starred_repos:
                        repo_star_counter.update([repo])

            acked_stargazers.update(stargazers_context.stargazers)

        # Calculating top-n repos by the number of stars given to them by stargazers
        # of source repositories
        return dict(
            Counter(repo_star_counter).most_common(self._context.max_popular_repos)
        )

    def _process_stargazer(self, stargazer):
        """
        Process single stargazer: fetch starred repos and taking them into account
        :param stargazer: user to process
        :return: user alongside with their starred repos
        """
        starred_context = StarredReposContext(user=stargazer)
        starred_context.repos = self._api_wrapper.fetch_starred_repositories(
            user=stargazer, progress=None, page_limit=self._context.page_limit
        )

        return stargazer, starred_context.repos

    @property
    def context(self):
        """
        :return: popular repositories context
        """
        return self._context
