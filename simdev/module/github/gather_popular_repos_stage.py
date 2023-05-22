import logging
from multiprocessing import Pool

from tqdm import tqdm

from simdev.module.git.github_api_wrapper import GithubApiWrapper
from simdev.util.pipeline import Pipeline, Stage

GATHER_POPULAR_REPOS_SAVE_FILENAME = 'gather_popular_repos_stage.json'
STARGAZERS_SAVE_FILENAME_TEMPLATE = 'stargazers/{}.json'
STARRED_SAVE_FILENAME_TEMPLATE = 'starred/{}.json'


class StargazersContext:
    """
    Context for storing info about repository's stargazers
    """

    def __init__(self, repo: str, page_limit: int):
        self.repo = repo
        self.page_limit = page_limit
        self.stargazers = []

    def recover(self):
        def hook(rec):
            if rec['repo'] == self.repo and rec['page_limit'] == self.page_limit:
                self.stargazers = set(rec['stargazers'])
                return self
            return None

        return Pipeline.load_context(hook=hook, name=STARGAZERS_SAVE_FILENAME_TEMPLATE.format(self.repo))

    def save(self):
        Pipeline.store_context(
            {
                'repo': self.repo,
                'stargazers': list(self.stargazers),
                'page_limit': self.page_limit
            },
            STARGAZERS_SAVE_FILENAME_TEMPLATE.format(self.repo))


class StarredReposContext:
    """
    Context for storing starred repositories of a user
    """

    def __init__(self, user: str, page_limit: int):
        self.user = user
        self.page_limit = page_limit
        self.repos: set[str] = set()

    def recover(self):
        def hook(rec):
            if rec['user'] == self.user and rec['page_limit'] == self.page_limit:
                self.repos = set(rec['repos'])
                return self
            return None

        return Pipeline.load_context(hook=hook, name=STARRED_SAVE_FILENAME_TEMPLATE.format(self.user))

    def save(self):
        Pipeline.store_context(
            {
                'user': self.user,
                'repos': list(self.repos),
                'page_limit': self.page_limit
            },
            STARRED_SAVE_FILENAME_TEMPLATE.format(self.user))


class PopularReposContext:
    """
    Context for storing info about repos that are popular among certain repo(-s') stargazers
    """

    def __init__(self,
                 source_repositories: list[str],
                 max_popular_repos_num: int,
                 page_limit: int,
                 api_tokens: list[str]):
        self.popular_repositories: dict[str, int] = {}
        self.source_repositories: list[str] = source_repositories
        self.api_tokens: list[str] = api_tokens
        self.max_popular_repos: int = max_popular_repos_num
        self.page_limit: int = page_limit

    def recover(self):
        rec = Pipeline.load_context(name=GATHER_POPULAR_REPOS_SAVE_FILENAME)
        if rec is None:
            return None
        if ('source_repositories' in rec and rec['source_repositories'] == self.source_repositories) \
                and ('max_popular_repos' in rec and rec['max_popular_repos'] == self.max_popular_repos) \
                and ('page_limit' in rec and rec['page_limit'] == self.page_limit):
            self.popular_repositories = rec['popular_repositories']
            return self
        return None

    def save(self):
        Pipeline.store_context({
            'source_repositories': self.source_repositories,
            'max_popular_repos': self.max_popular_repos,
            'popular_repositories': self.popular_repositories,
            'page_limit': self.page_limit
        }, GATHER_POPULAR_REPOS_SAVE_FILENAME)


class GatherPopularReposStage(Stage[PopularReposContext]):
    """
    Stage for gathering popular repositories among stargazers of source repositories
    """

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
        starred_context = StarredReposContext(user=stargazer, page_limit=self._context.page_limit)
        if starred_context.recover() is None:
            starred_context.repos = self._api_wrapper.fetch_starred_repositories(
                user=stargazer,
                progress=None,
                page_limit=self._context.page_limit)
            starred_context.save()

        return stargazer, starred_context.repos

    def run(self, pipeline: Pipeline):
        recovered = self._context.recover()
        if recovered is not None:
            logging.info(
                'Popular repos have been recovered from file. If you want to run this again, '
                F'delete {GATHER_POPULAR_REPOS_SAVE_FILENAME}')
            return

        source_tqdm = tqdm(self._context.source_repositories, desc='Coursing through source repositories')
        repo_star_count_map = {}

        accounted_stargazers = set()

        for source_repo in source_tqdm:
            stargazers_context = StargazersContext(source_repo, self._context.page_limit)
            if stargazers_context.recover() is None:
                stargazers_context.stargazers = self._api_wrapper.fetch_stargazers(repo=source_repo,
                                                                                   progress=source_tqdm,
                                                                                   page_limit=self._context.page_limit)
                stargazers_context.save()

            selection = stargazers_context.stargazers - accounted_stargazers

            with Pool(processes=6) as pool:
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
        popular = sorted(repo_star_count_map, key=lambda key: repo_star_count_map[key], reverse=True)
        result_dict = {}
        for repository in popular[:self._context.max_popular_repos]:
            result_dict.update({repository: repo_star_count_map[repository]})

        self._context.popular_repositories = result_dict
        self._context.save()

    @property
    def context(self):
        return self._context
