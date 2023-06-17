import logging
from pathlib import Path
from typing import Dict, List, Optional

import click

from simdev.module.git.repo_info_extractor import RepoInfoExtractor
from simdev.module.github.popular_repos_extractor import PopularReposExtractor
from simdev.module.simdev.similar_dev_searcher import SimilarDevSearcher
from simdev.util.export_utils import create_and_write, read_json
from simdev.util.url_utils import github_repo_name_to_url


@click.group(invoke_without_command=True, no_args_is_help=True)
def simdev():
    """
    Similar developer search. Used to extract and transform open data (public
    GitHub repositories) to find those developers whose way to code is similar.

    Packed in a CLI providing utilities (steps) to achieve the final goal.

    Made for HSE Course: Code as Data by Alexey Akhundov (@theseems)
    """
    pass


@simdev.command(name='top', short_help='Get top-n popular repositories starred by '
                                       'stargazers of provided initial repositories')
@click.option('--source',
              default=['TheSeems/TMoney'],
              multiple=True,
              help='List of initial repositories to get top starred by stargazers of')
@click.option('--tokens',
              default=None,
              multiple=True,
              help='List of GitHub API tokens to fetch information with')
@click.option('--processes',
              default=6,
              type=int,
              help='Number of processes to fetch starred repositories in')
@click.option('--count',
              default=100,
              type=int,
              help='Max amount of top popular repositories to get')
@click.option('--page_limit',
              default=400,
              type=int,
              help='GitHub API page limit')
@click.option('--export',
              type=click.Path(dir_okay=False, file_okay=True),
              default=Path('results') / 'popular_repos.json')
def get_top_repos(source: List[str],
                  tokens: List[str],
                  processes: int,
                  count: int,
                  page_limit: int,
                  export: str) -> None:
    """
    Get top-n popular repositories among stargazers of source repositories
    and print them
    :param source: List of URLs to GitHub source repositories
    (--source a --source b -> [a, b])
    :param tokens: GitHub API tokens to fetch information with
    :param processes: Number of processes to fetch starred repositories in
    :param count: Max amount of top popular repositories to get (top-100, top-10, etc.)
    :param page_limit: GitHub API page limit
    :param export: Path to export json results to
    """
    extractor = PopularReposExtractor(
        source_repos=source,
        api_tokens=tokens,
        max_popular_repos_num=count,
        stargazers_fetch_process_count=processes,
        page_limit=page_limit
    )
    extractor.extract()
    create_and_write(extractor.popular_repos, export)


@simdev.command(name='clone', short_help='Clone repositories and fetch info about them')
@click.option('--source',
              default=['https://github.com/TheSeems/TMoney'],
              multiple=True,
              help='List of repositories to fetch information about')
@click.option('--limit',
              default=10_000,
              type=int,
              help='Max amount of commits to process')
@click.option('--load',
              default=None,
              type=click.Path(dir_okay=False, file_okay=True, readable=True),
              help='Path to popular repositories to load repositories from. '
                   'Overrides --source option')
@click.option('--export',
              type=click.Path(dir_okay=False, file_okay=True),
              default=Path('results') / 'dev_info.json',
              help='Path to store results to')
def clone_repos(source: List[str],
                limit: int,
                load: Optional[str],
                export: str) -> None:
    """
    Clone repositories & print information about them
    :param source: List of URLs to GitHub repositories to clone and get info about
    :param limit: Max amount of commits to process
    :param load: Path to popular repositories to load repositories from.
    Overrides --source option
    :param export: Path to export json results to
    """
    if load is not None:
        # Popular repositories dict from `top` command
        popular_repos: Dict[str, int] = read_json(load)
        # Converting GitHub notation to URLs
        source = list(map(github_repo_name_to_url, popular_repos.keys()))
    extractor = RepoInfoExtractor(repo_urls=source, max_commit_count=limit)
    extractor.extract()
    create_and_write(extractor.dev_info, export)


@simdev.command(name='search', short_help='Search for developers similar for given dev')
@click.option('--source',
              help='Email of the developer to find similar developers to',
              required=True)
@click.option('--info',
              type=click.Path(dir_okay=False, file_okay=True, exists=True),
              required=True,
              help='Path to dev info file (computer during `clone` command)')
@click.option('--export',
              type=click.Path(dir_okay=False, file_okay=True),
              default=None,
              help='Path to store results to')
@click.option('--limit',
              default=10,
              help='How many developers to search for at most (with highest '
                   'similarity score)')
def search(source: str, info: str, export: Optional[str], limit: int) -> None:
    """
    Clone repositories & print information about them
    :param source: Email of the developer to find similar to
    :param info: Path to computed during clone developers info
    :param export: Path to the result file
    (json content: from developer to score that reflects the degree of similarity)
    :param limit: How many developers to search for at most
    (with the highest similarity score)
    """
    if export is None:
        export = Path("results") / "similar" / F"{source}.json"
    searcher = SimilarDevSearcher(dev_info=read_json(info), max_results_count=limit)
    result = searcher.search(source)
    create_and_write(result, export)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('pydriller.repository')
    logger.setLevel(logging.WARN)
    simdev()
