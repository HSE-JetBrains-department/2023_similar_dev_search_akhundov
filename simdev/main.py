from typing import List

import click

from simdev.module.github.gather_popular_repos_stage import GatherPopularReposStage
from simdev.util.pipeline import Pipeline

# Main pipeline object used by all the subcommands
main_pipeline = Pipeline()


@click.group()
def simdev():
    """
    Similar developer search. Used to extract and transform open data (public
    GitHub repositories) to find those developers whose way to code is similar.

    Packed in a CLI providing utilities (steps) to achieve the final goal.
    """
    pass


@simdev.command(name='top', short_help='Get top-n popular repositories starred by '
                                       'stargazers of provided initial repositories')
@click.option('--sources', default=['pytorch/pytorch'],
              help='List of initial repositories to get top starred by stargazers of')
@click.option('--tokens', default=None,
              help='List of GitHub API tokens to fetch information with')
@click.option('--processes', default=6,
              help='Number of processes to fetch starred repositories in')
@click.option('--count', default=6,
              help='Number of top popular repositories to get')
@click.option('--page_limit', default=400,
              help='GitHub API page limit')
def get_top_repos(source_repos: List[str],
                  tokens: List[str],
                  processes: int,
                  count: int,
                  page_limit: int):
    main_pipeline.append(GatherPopularReposStage(
        source_repos=source_repos,
        api_tokens=tokens,
        max_popular_repos_num=count,
        stargazers_fetch_process_count=processes,
        page_limit=page_limit))
    main_pipeline.run()


if __name__ == "__main__":
    simdev()
