import json
import os
from typing import Any


def create_and_write(results: Any, path: str) -> None:
    """
    Create necessary dirs and files and then json dump the results
    :param results: to dump
    :param path: to save to
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fout:
        json.dump(results, fout, indent=4, sort_keys=True)


def read_json(path: str) -> Any:
    """
    Read json from file
    :param path: path to the file
    :return: read contents (json)
    """
    with open(path, "r") as fin:
        return json.load(fin)
