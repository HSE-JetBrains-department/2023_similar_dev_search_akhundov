import logging
import sys

from simdev.util.pipeline_exception import PipelineException


class Pipeline:
    def __init__(self):
        self.stages = []
        self.pastStages = []
        self.currentStage = None

    def run(self):
        print('Pipeline structure:', ' -> '.join(map(lambda element: element.name, self.stages)))
        for stage in self.stages:
            print('Running:', stage.name)
            try:
                stage.run(self)
            except PipelineException as e:
                logging.error('Blocking issue is observed executing the pipeline:', e, file=sys.stderr)
                logging.error('Order:', ' -> '.join(map(lambda past: past.name, self.pastStages + [stage])), file=sys.stderr)
            except Exception as e:
                logging.error('An unexpected failure occurred executing the pipeline. Please, refer to the '
                                'following details',
                                file=sys.stderr)
                logging.error('Order:', ' -> '.join(map(lambda past: past.name, self.pastStages + [stage])), file=sys.stderr)
                raise e
            self.pastStages += [stage]

    def append(self, stage):
        self.stages += [stage]

    def get_stage_context(self, stage_type: type):
        for stage in self.stages:
            if isinstance(stage, stage_type):
                return stage.context
        return None
