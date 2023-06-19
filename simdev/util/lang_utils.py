from typing import Optional

import enry


def classify_language(name: str, contents: bytes, path: str) -> Optional[str]:
    """
    Classify programming languages used in the file
    :param name: name of the file
    :param contents: raw contents of the file
    :param path: local path to the file
    :return: classified programming language if any
    """

    # Check if file is suitable for programming languages classification:
    # configurations, documentation, binaries etc. are skipped
    if contents is None or \
            enry.is_binary(contents) or \
            enry.is_vendor(name) or \
            enry.is_generated(name, contents) or \
            (path is not None and
             (enry.is_image(path) or
              enry.is_configuration(path) or
              enry.is_documentation(path) or
              enry.is_dot_file(path))):
        return

    prog_language = enry.get_language(name, contents)
    if len(prog_language) == 0:
        return None
    else:
        return prog_language
