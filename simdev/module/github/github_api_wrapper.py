import json
import logging
import random
from typing import Any, Dict, List, Set, Union

import requests as requests
import tqdm as tqdm
from requests.adapters import HTTPAdapter, Retry

from simdev.util.pipeline import PipelineCache

# Type for GitHub response for fetching starred repositories
starred_response_type = Union[List[Dict[str, str]], Dict[str, str], None]


def _is_rate_limit_reached(page_response: starred_response_type):
    """
    Check by the response if the rate limit has been reached
    :param page_response: response object
    :return: if the rate limit was reached
    """
    return page_response is not None \
        and "message" in page_response \
        and "rate limit" in page_response["message"]


def _is_response_not_found(page_response: starred_response_type):
    """
    Check by the response if content is not found
    :param page_response: response object
    :return: if the content requested was not found
    """
    return len(page_response) == 0 or \
        ("message" in page_response and page_response["message"] == "Not Found")


def _report_unknown_response(response: Any, url: str):
    """
    Report unexpected response
    :param response: actual response object
    :param url: requested url
    """
    logging.warning("Unexpected response: %s", json.dumps(response))
    logging.warning("Request: %s", url)


def _update_tqdm_page_postfix(progress: tqdm.tqdm, page: int):
    """
    Update TQDM postfix rolling over pages
    :param progress: to update
    :param page: current page number
    """
    if progress is not None:
        progress.set_postfix_str(F"page {page}")


class GithubApiWrapper:
    """
    Wrapper for GitHub API to fetch stargazers and starred
    repos utilizing retries and personal access tokens
    """

    def __init__(
        self,
        api_tokens: Union[List[str], None] = None,
        github_api_url: str = "https://api.github.com/",
        max_retries_num: int = 1000,
    ):
        """
        Initialize GitHub API wrapper
        with parameters to use in order to fetch info from GitHub
        :param api_tokens: list of GitHub API tokens
        :param github_api_url: URL of GitHub API
        :param max_retries_num: max number of retries
        fetching content from GitHub
        """
        self._api_url = github_api_url
        self._max_retries_num = max_retries_num
        self._headers: Dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._api_tokens = api_tokens
        self._current_api_token: str | None = None
        self._update_api_token()

        # Making these functions get data from cache if possible
        self.fetch_stargazers = PipelineCache.memory.cache(
            func=self.fetch_stargazers, ignore=["progress", "batch_count", "page_limit"]
        )
        self.fetch_starred_repositories = PipelineCache.memory.cache(
            func=self.fetch_starred_repositories,
            ignore=["progress", "batch_count", "page_limit"],
        )

    def fetch_stargazers(
            self, repo: str, batch_count=100, page_limit=400,
            progress: tqdm.tqdm = None
    ) -> Set[str]:
        """
        Fetch stargazers of the repository
        :param repo: name (GitHub flavoured. Example: theseems/HseNotebooks)
        :param batch_count: entries per GitHub API response page
        :param page_limit: max amount of pages to fetch
        :param progress: TQDM progress if any
        :return: set of stargazers
        """
        if progress is not None:
            progress.desc = f"Fetching stargazers for {repo}"

        fixed_url_part = (
            f"{self._api_url}repos/{repo}/stargazers?per_page={str(batch_count)}&page="
        )
        current_page = 0
        result: Set[str] = set()

        while True:
            full_url = F"{fixed_url_part}{current_page}"
            _update_tqdm_page_postfix(progress, current_page + 1)
            page_response: List[Dict[str, Any]] = self._get_request_json(full_url)
            if len(page_response) == 0:
                break
            if not isinstance(page_response, list):
                _report_unknown_response(page_response, full_url)
                continue
            for stargazer in page_response:
                result.add(stargazer["login"])
            current_page += 1
            if current_page > page_limit:
                break
        return result

    def fetch_starred_repositories(
            self, user: str, batch_count=100, page_limit=400,
            progress: tqdm.tqdm = None
    ) -> Set[str]:
        """
        Fetch repositories starred by a user
        :param user: to fetch starred repositories of
        :param batch_count: number of entries per GitHub API response's page
        :param page_limit: max amount of pages to fetch
        :param progress: TQDM progress
        :return: set of starred repositories
        """
        if progress is not None:
            progress.desc = f"Fetching starred repositories of {user}"

        fixed_url_part = \
            f"{self._api_url}users/{user}/starred?per_page={batch_count}&page="

        current_page = 0
        result: Set[str] = set()

        while True:
            full_url = F"{fixed_url_part}{current_page}"
            page_response: starred_response_type = None
            try:
                _update_tqdm_page_postfix(progress, current_page + 1)
                page_response = self._get_request_json(full_url)
                if _is_response_not_found(page_response):
                    break
                for repo in page_response:
                    result.add(repo["full_name"])
            except Exception:
                if _is_rate_limit_reached(page_response):
                    self._update_api_token()
                _report_unknown_response(page_response, full_url)
                continue
            current_page += 1
            if current_page > page_limit:
                break
        return result

    def _update_api_token(self):
        """
        Switch to using another GitHub API token if possible
        """
        if self._api_tokens is None:
            return
        if len(self._api_tokens) == 0:
            self._current_api_token = None
        elif len(self._api_tokens) == 1:
            self._current_api_token = self._api_tokens[0]
        elif self._current_api_token is None:
            self._current_api_token = random.choice(self._api_tokens)
        else:
            new_token_pool = set(self._api_tokens)
            new_token_pool.remove(self._current_api_token)
            self._current_api_token = random.choice(list(new_token_pool))
        if self._current_api_token is not None:
            self._headers.update({"Authorization": f"Bearer {self._current_api_token}"})

    def _get_request_json(self, url: str):
        """
        Send GET request and retrieve a response as json
        :param url: to send a request to
        :return: json response
        """
        retries = Retry(total=self._max_retries_num, backoff_factor=1)
        session = requests.Session()
        session.headers = self._headers
        session.mount("https://", HTTPAdapter(max_retries=retries))
        result = None
        while result is None:
            try:
                result = session.get(url).json()
            except Exception:
                continue
        return result
