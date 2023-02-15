from module.git.clone_stage import CloneStage, CloneContext
from util.pipeline import Pipeline

if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.append(CloneStage(CloneContext(repository_urls=[
        'https://github.com/HSE-JetBrains-department/2023_similar_dev_search_akhundov',
        'https://github.com/HSE-JetBrains-department/similar_project_search_elastic',
        'https://github.com/HSE-JetBrains-department/codex_like_dataset_generation'
    ])))
    pipeline.run()

    clone_context = pipeline.get_stage_context(CloneStage)
    for repository in clone_context.repositories:
        print('Contributors of %s:' % repository.url)
        for (contributor, contributor_context) in repository.contributors.items():
            print(' %s' % contributor)
            for filename, file_context in contributor_context.files.items():
                print('  %s -- +%s -%s (total changed=%s)' % (filename, file_context.added_lines,
                             file_context.deleted_lines, file_context.changed_lines))
