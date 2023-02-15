class PipelineException(Exception):
    """
    Raised when a deliberate inconsistency is observed in a pipeline.
    This exception is unique compared to others, as it is used to inform the user about their inconsistent input
    or when any predictable pipeline-blocking situation is observed
    """
    pass
