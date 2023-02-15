from abc import ABC, abstractmethod, ABCMeta
from typing import TypeVar, Generic

from simdev.util.pipeline import Pipeline

T = TypeVar("T")


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
