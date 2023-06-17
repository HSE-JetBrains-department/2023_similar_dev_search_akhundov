import json
import os
from typing import Any


def create_and_write(results: Any, path: str, sort_keys: bool = True) -> None:
    """
    Create necessary dirs and files and then json dump the results
    :param results: to dump
    :param sort_keys: sort keys like in json dump: If sort_keys is true,
    then the output of dictionaries will be sorted by key.
    :param path: to save to
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fout:
        json.dump(results, fout, indent=4, sort_keys=sort_keys)


def read_json(path: str) -> Any:
    """
    Read json from file
    :param path: path to the file
    :return: read contents (json)
    """
    with open(path, "r") as fin:
        return json.load(fin)
