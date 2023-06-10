import logging
from abc import ABC, ABCMeta, abstractmethod
from typing import Generic, List, TypeVar

from joblib import Memory

T = TypeVar("T")


class PipelineException(Exception):
    """
    Raised when a deliberate inconsistency is observed in a pipeline.
    This exception is unique compared to others,
    as it is used to inform the user about their inconsistent input
    or when any predictable pipeline-blocking situation is observed
    """


class PipelineCache:
    """
    Utility class that stores pipeline cache (for stages)
    """

    memory = Memory("cache", verbose=False)


class Pipeline:
    """
    The main class for the pipeline.
    Pipeline consists of stages.
    Each stage represents a single step we take to get to the result
    """

    def __init__(self):
        """
        Initialize pipeline with list of stages (empty at the beginning) and a list
        of stages previously ran to allow for getting the information from their
        context in the future
        """
        self.stages: List[Stage] = []
        self.past_stages: List[Stage] = []

    def run(self):
        """
        Run all the stages in the pipeline handling
        all the exceptions, printing the order of execution and
        storing ran stages
        """
        logging.info(
            "Pipeline structure: %s",
            " -> ".join(map(lambda element: element.name, self.stages)),
        )
        for stage in self.stages:
            logging.info("Running: %s", stage.name)
            try:
                stage.run(self)
            except PipelineException as exception:
                logging.error(
                    "Blocking issue is observed executing the pipeline: %s", exception
                )
                logging.error(
                    "Order: %s",
                    " -> ".join(
                        map(lambda past: past.name, self.past_stages + [stage])
                    ),
                )
                raise exception
            except Exception as exception:
                logging.error(
                    "An unexpected failure occurred executing the pipeline. Please, "
                    "refer to the following details"
                )
                logging.error(
                    "Order: %s",
                    " -> ".join(
                        map(lambda past: past.name, self.past_stages + [stage])
                    ),
                )
                raise exception
            self.past_stages.append(stage)

    def append(self, stage):
        """
        Append stage to the pipeline
        :param stage: to append
        """
        self.stages.append(stage)

    def get_stage_context(self, stage_type: type):
        """
        Get stage's context that stores arbitrary information supplied/produced
        :param stage_type: type of the stage to get the context of
        :return: context if any
        """
        for stage in self.stages:
            if isinstance(stage, stage_type):
                return stage.context
        return None


class Stage(ABC, Generic[T]):
    """
    An atomic step in a pipeline that encapsulates logic for a complex action
    """

    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def context(self):
        """
        Context object of the stage
        """
        raise NotImplementedError("Context is not implemented")

    @property
    @abstractmethod
    def name(self):
        """
        Name of the stage
        """
        raise NotImplementedError("Name is not implemented")

    @abstractmethod
    def run(self, pipeline: Pipeline):
        """
        Method that embodies stage's logic: execution happens here
        :param pipeline: pipeline inside which a stage is run
        """
        raise NotImplementedError("Run is not implemented")
