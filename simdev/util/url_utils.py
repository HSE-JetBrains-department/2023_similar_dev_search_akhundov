# GitHub public URL
GITHUB_URL = "https://github.com"


def github_repo_name_to_url(notation: str):
    """
    Transform GitHub repository notation (<organization|username>/<repo_name>) to
    URL on the domain GitHub.com
    :param notation: GitHub repository notation
    :return: URL to the repository
    """
    return F"{GITHUB_URL}/{notation}"
