from typing import TypeVar

from joblib import Memory

T = TypeVar("T")


class PipelineCache:
    """
    Utility class that stores pipeline cache (for stages)
    """

    memory = Memory("cache", verbose=False)
