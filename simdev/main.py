import logging
from pathlib import Path
from typing import List

import click

from simdev.module.git.repo_info_extractor import RepoInfoExtractor
from simdev.module.github.popular_repos_extractor import PopularReposExtractor
from simdev.util.export_utils import create_and_write


@click.group(invoke_without_command=True, no_args_is_help=True)
@click.version_option(prog_name='simdev',
                      message='simdev %(version)s',
                      version='0.1')
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
@click.option('--tokens', default=None, multiple=True,
              help='List of GitHub API tokens to fetch information with')
@click.option('--processes', default=6, type=int,
              help='Number of processes to fetch starred repositories in')
@click.option('--count', default=100, type=int,
              help='Max amount of top popular repositories to get')
@click.option('--page_limit', default=400, type=int,
              help='GitHub API page limit')
@click.option('--export', type=click.Path(dir_okay=False, file_okay=True),
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
@click.option('--export', type=click.Path(dir_okay=False, file_okay=True),
              default=Path('results') / 'repo_info.json')
def clone_repos(source: List[str], export: str) -> None:
    """
    Clone repositories & print information about them
    :param source: list of URLs to GitHub repositories to clone and get info about
    :param export: Path to export json results to
    """
    extractor = RepoInfoExtractor(source)
    extractor.extract()
    create_and_write(extractor.dev_info, export)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    simdev()
