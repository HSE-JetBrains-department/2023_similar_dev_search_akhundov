from collections import Counter
from multiprocessing import Pool
from typing import Dict, List, Set, Tuple

from tqdm import tqdm

from simdev.module.github.github_api_wrapper import GithubApiWrapper
from simdev.util.pipeline import PipelineCache


class PopularReposExtractor:
    """
    Stage for gathering popular repositories among stargazers of source repositories
    """

    def __init__(
            self,
            source_repos: List[str],
            max_popular_repos_num: int,
            page_limit: int,
            api_tokens: List[str],
            stargazers_fetch_process_count: int,
    ):
        """
        Initialize stage with input params
        :param source_repos: list of URLs to
        GitHub repositories
        :param max_popular_repos_num: max number of produced (most popular) repositories
        :param page_limit: GitHub API page limit
        :param api_tokens: list of GitHub API tokens
        :param stargazers_fetch_process_count the number
        of processes to fetch stargazers in
        """
        self._api_wrapper = GithubApiWrapper(api_tokens=api_tokens)
        self.source_repos = source_repos
        self.max_popular_repos_num = max_popular_repos_num
        self.stargazers_fetch_process_count = stargazers_fetch_process_count
        self.page_limit = page_limit
        self._popular_repos: Dict[str, int] = {}

        # Cache the main fetching function
        self.extract = PipelineCache.memory.cache(self.extract)

    def extract(self):
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
            self.source_repos,
            desc="Coursing through source repositories",
        )
        repo_star_counter = Counter()

        # Acknowledged stargazers maintained to avoid duplicates between several
        # source repositories
        acked_stargazers: Set[str] = set()

        for source_repo in source_tqdm:
            stargazers = self._api_wrapper.fetch_stargazers(
                repo=source_repo,
                progress=source_tqdm,
                page_limit=self.page_limit,
            )

            selection = stargazers - acked_stargazers
            with Pool(processes=self.stargazers_fetch_process_count) as pool:
                starred_repos_progress = tqdm(
                    pool.imap(self._process_stargazer, selection),
                    total=len(selection),
                    desc=f"Get starred repos for stargazers of {source_repo}",
                )

                for stargazer, starred_repos in starred_repos_progress:
                    for repo in starred_repos:
                        repo_star_counter.update([repo])

            acked_stargazers.update(stargazers)

        # Calculating top-n repos by the number of stars given to them by stargazers
        # of source repositories
        self._popular_repos = \
            dict(Counter(repo_star_counter).most_common(self.max_popular_repos_num))

    @property
    def popular_repos(self):
        """
        :return: computer popular repositories dict
        (GitHub notation of repo to the number of stargazers)
        """
        return self._popular_repos

    def _process_stargazer(self, stargazer: str) -> Tuple[str, Set[str]]:
        """
        Process single stargazer: fetch starred repos and taking them into account
        :param stargazer: user to process
        :return: user alongside with their starred repos
        """
        return stargazer, self._api_wrapper.fetch_starred_repositories(
            user=stargazer,
            progress=None,
            page_limit=self.page_limit
        )
