import logging
from collections import Counter
from multiprocessing import Pool
from os import path

from tqdm import tqdm

from simdev.module.github.github_api_wrapper import GithubApiWrapper
from simdev.util.pipeline import Pipeline, Stage


class StargazersContext:
    """
    Context for storing info about repository's stargazers
    """

    def __init__(self, repo: str, page_limit: int, stargazers_save_directory: str):
        self.repo = repo
        self.page_limit = page_limit
        self.stargazers_save_directory = stargazers_save_directory
        self.stargazers: set[str] = set()

    def recover(self):
        """
        Recover stargazer list from the save file (only matching page_limit)
        :return: self if recovery went successful or None otherwise
        """

        def hook(recovered):
            if recovered['repo'] == self.repo and recovered['page_limit'] == self.page_limit:
                self.stargazers = set(recovered['stargazers'])
                return self
            return None

        return Pipeline.load_context(hook=hook,
                                     name=path.join(self.stargazers_save_directory, '{0}.json'.format(self.repo)))

    def save(self):
        """
        Store stargazers list alongside page limit (and repo) in the save file
        """
        Pipeline.store_context(
            {
                'repo': self.repo,
                'stargazers': list(self.stargazers),
                'page_limit': self.page_limit
            },
            path.join(self.stargazers_save_directory, '{0}.json'.format(self.repo)))


class StarredReposContext:
    """
    Context for storing starred repositories of a user
    """

    def __init__(self, user: str, page_limit: int, starred_repos_save_directory: str):
        self.user = user
        self.page_limit = page_limit
        self.starred_repos_save_directory = starred_repos_save_directory
        self.repos: set[str] = set()

    def recover(self):
        """
        Recover repositories starred by specific user
        :return: self if recovery went successful or None otherwise
        """

        def hook(rec):
            if rec['user'] == self.user and rec['page_limit'] == self.page_limit:
                self.repos = set(rec['repos'])
                return self
            return None

        return Pipeline.load_context(hook=hook,
                                     name=path.join(self.starred_repos_save_directory, '{0}.json'.format(self.user)))

    def save(self):
        Pipeline.store_context(
            {
                'user': self.user,
                'repos': list(self.repos),
                'page_limit': self.page_limit
            },
            path.join(self.starred_repos_save_directory, '{0}.json'.format(self.user)))


class PopularReposContext:
    """
    Context for storing info about repos that are popular among certain repo(-s') stargazers
    """

    def __init__(self,
                 source_repositories: list[str],
                 max_popular_repos_num: int,
                 page_limit: int,
                 api_tokens: list[str],
                 save_filename: str,
                 starred_repos_save_directory: str,
                 stargazers_save_directory: str):
        self.popular_repositories = {}
        self.source_repositories = source_repositories
        self.api_tokens = api_tokens
        self.max_popular_repos = max_popular_repos_num
        self.page_limit = page_limit
        self.save_filename = save_filename
        self.starred_repos_save_directory = starred_repos_save_directory
        self.stargazers_save_directory = stargazers_save_directory

    def recover(self):
        """
        Recover computed repositories from the save file. This method accounts for the rest of parameters. For
        example, we cannot use results if page limit to get them is different that what's requested in this
        particular stage run
        :return: self if recovery went successful or None otherwise
        """
        rec = Pipeline.load_context(name=self.save_filename)
        if rec is None:
            return None
        if ('source_repositories' in rec and rec['source_repositories'] == self.source_repositories) \
                and ('max_popular_repos' in rec and rec['max_popular_repos'] == self.max_popular_repos) \
                and ('page_limit' in rec and rec['page_limit'] == self.page_limit):
            self.popular_repositories = rec['popular_repositories']
            return self
        return None

    def save(self):
        """
        Save computed repositories alongside with parameters used to get them in a file
        """
        Pipeline.store_context({
            'source_repositories': self.source_repositories,
            'max_popular_repos': self.max_popular_repos,
            'popular_repositories': self.popular_repositories,
            'page_limit': self.page_limit
        }, self.save_filename)


class GatherPopularReposStage(Stage[PopularReposContext]):
    """
    Stage for gathering popular repositories among stargazers of source repositories
    """

    # Number of processes to fetch starred repositories from GitHub in
    STARRED_REPOS_FETCH_PROCESS_COUNT = 6

    @property
    def name(self):
        return "Gather popular repositories"

    def __init__(self, context: PopularReposContext):
        self._context = context
        self._api_wrapper = GithubApiWrapper(api_tokens=context.api_tokens)

    def _process_stargazer(self, stargazer):
        """
        Process single stargazer: fetch starred repos and taking them into account
        :param stargazer: user to process
        :return: user alongside with their starred repos
        """
        starred_context = StarredReposContext(user=stargazer,
                                              page_limit=self._context.page_limit,
                                              starred_repos_save_directory=self._context.starred_repos_save_directory)
        if starred_context.recover() is None:
            starred_context.repos = self._api_wrapper.fetch_starred_repositories(
                user=stargazer,
                progress=None,
                page_limit=self._context.page_limit)
            starred_context.save()

        return stargazer, starred_context.repos

    def run(self, pipeline: Pipeline):
        """
        First of all, we fetch all the stargazers for requested repositories (merge them not to include duplicates).
        Then we run over all the stargazers and fetch their starred repositories (saving intermediate results if
        possible). After that we accumulate all the results and determine top-n repositories starred by initial
        stargazers.
        :param pipeline: pipline inside which the stage is run
        :return: top-n repositories by star count among stargazers of initial repositories
        """
        recovered = self._context.recover()
        if recovered is not None:
            logging.info(
                'Popular repos have been recovered from file. If you want to run this again, '
                F'delete {self._context.save_filename}')
            return

        source_tqdm = tqdm(self._context.source_repositories, desc='Coursing through source repositories')
        repo_star_count_map = {}

        accounted_stargazers = set()

        for source_repo in source_tqdm:
            stargazers_context = StargazersContext(repo=source_repo,
                                                   page_limit=self._context.page_limit,
                                                   stargazers_save_directory=self._context.stargazers_save_directory)
            if stargazers_context.recover() is None:
                stargazers_context.stargazers = self._api_wrapper.fetch_stargazers(repo=source_repo,
                                                                                   progress=source_tqdm,
                                                                                   page_limit=self._context.page_limit)
                stargazers_context.save()

            selection = stargazers_context.stargazers - accounted_stargazers

            with Pool(processes=GatherPopularReposStage.STARRED_REPOS_FETCH_PROCESS_COUNT,
                      initializer=_init_pool,
                      initargs=[Pipeline.SAVES_DIRECTORY]) as pool:
                starred_repos_progress = tqdm(
                    pool.imap(self._process_stargazer, selection),
                    total=len(selection),
                    desc='Get starred repos for stargazers of ' + source_repo)

                for (stargazer, starred_repos) in starred_repos_progress:
                    for repo in starred_repos:
                        if repo in repo_star_count_map:
                            repo_star_count_map[repo] += 1
                        else:
                            repo_star_count_map[repo] = 1

            accounted_stargazers.update(stargazers_context.stargazers)

        # Calculating top-n repos by the number of stars given to them by stargazers
        # of source repositories
        self._context.popular_repositories = dict(
            Counter(repo_star_count_map).most_common(self._context.max_popular_repos))
        self._context.save()

    @property
    def context(self):
        return self._context


def _init_pool(saves_directory: str):
    """
    A function to initialize pool. Used to fill in statics working in multiprocess environment
    """
    Pipeline.SAVES_DIRECTORY = saves_directory
