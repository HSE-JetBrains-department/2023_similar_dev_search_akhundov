import logging

from abc import ABC, abstractmethod, ABCMeta
from typing import TypeVar, Generic

T = TypeVar("T")


class PipelineException(Exception):
    """
    Raised when a deliberate inconsistency is observed in a pipeline.
    This exception is unique compared to others, as it is used to inform the user about their inconsistent input
    or when any predictable pipeline-blocking situation is observed
    """
    pass


class Pipeline:
    def __init__(self):
        self.stages = []
        self.pastStages = []
        self.currentStage = None

    def run(self):
        logging.info('Pipeline structure: ' + ' -> '.join(map(lambda element: element.name, self.stages)))
        for stage in self.stages:
            logging.info('Running: ' + stage.name)
            try:
                stage.run(self)
            except PipelineException as e:
                logging.error('Blocking issue is observed executing the pipeline: %s', e)
                logging.error('Order: %s', ' -> '.join(map(lambda past: past.name, self.pastStages + [stage])))
            except Exception as e:
                logging.error('An unexpected failure occurred executing the pipeline. Please, refer to the '
                              'following details')
                logging.error('Order: %s', ' -> '.join(map(lambda past: past.name, self.pastStages + [stage])))
                raise e
            self.pastStages += [stage]

    def append(self, stage):
        self.stages += [stage]

    def get_stage_context(self, stage_type: type):
        for stage in self.stages:
            if isinstance(stage, stage_type):
                return stage.context
        return None


class Stage(ABC, Generic[T]):
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def context(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def run(self, pipeline: Pipeline):
        pass
