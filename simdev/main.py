import logging
from typing import List

import click

from simdev.module.git.clone_stage import CloneContext, CloneStage
from simdev.module.github.gather_popular_repos_stage import GatherPopularReposStage
from simdev.util.pipeline import Pipeline

# Main pipeline object used by all the subcommands
main_pipeline = Pipeline()


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
def get_top_repos(source: List[str],
                  tokens: List[str],
                  processes: int,
                  count: int,
                  page_limit: int):
    """
    Get top-n popular repositories among stargazers of source repositories
    and print them
    :param source: list of URLs to GitHub source repositories
    :param tokens: GitHub API tokens to fetch information with
    :param processes: Number of processes to fetch starred repositories in
    :param count: Max amount of top popular repositories to get (top-100, top-10, etc.)
    :param page_limit: GitHub API page limit
    """
    main_pipeline.append(
        GatherPopularReposStage(
            source_repos=source,
            api_tokens=tokens,
            max_popular_repos_num=count,
            stargazers_fetch_process_count=processes,
            page_limit=page_limit
        )
    )
    main_pipeline.run()
    print(main_pipeline.get_stage_context(GatherPopularReposStage).popular_repositories)


@simdev.command(name='clone', short_help='Clone repositories and fetch info about them')
@click.option('--source',
              default=['https://github.com/TheSeems/TMoney'],
              multiple=True,
              help='List of repositories to fetch information about')
def clone_repos(source: List[str]):
    """
    Clone repositories & print information about them
    :param source: list of URLs to GitHub repositories to clone and get info about
    """
    main_pipeline.append(CloneStage(source))
    main_pipeline.run()
    stage_context: CloneContext = main_pipeline.get_stage_context(CloneStage)
    repos = stage_context.repo_contexts
    for repo in repos:
        print(F'Repository {repo.url}')
        for (contributor, contributor_context) in repo.contributors.items():
            print(F'\t{contributor.name}:')
            for (filename, file_context) in contributor_context.files.items():
                print(F'\t\t[{file_context.prog_language}]', F'{filename}:',
                      F'+{file_context.added_lines}', F'-{file_context.deleted_lines}')
            print('')
        print('')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    simdev()
