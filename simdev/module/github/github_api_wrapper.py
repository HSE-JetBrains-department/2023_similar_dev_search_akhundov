import json
import logging
import random

import requests as requests
from requests.adapters import HTTPAdapter, Retry

starred_response_type = list[dict[str]] | dict[str] | None


class GithubApiWrapper:
    """
    Wrapper for GitHub API to fetch stargazers and starred repos utilizing retries and personal access tokens
    """

    def __init__(self,
                 api_tokens: list[str] = None,
                 github_api_url: str = "https://api.github.com/",
                 max_retries_num: int = 1000):
        self._api_url: str = github_api_url
        self._max_retries_num: int = max_retries_num

        self._headers: dict[str] = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

        self._api_tokens: list[str] = api_tokens
        self._current_api_token: str | None = None
        self._update_api_token()

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
            self._headers.update({'Authorization': 'Bearer ' + self._current_api_token})

    def _get_request_json(self, url):
        """
        Send GET request and retrieve a response as json
        :param url: to send a request to
        :return: json response
        """
        retries = Retry(total=self._max_retries_num, backoff_factor=1)
        session = requests.Session()
        session.headers = self._headers
        session.mount('https://', HTTPAdapter(max_retries=retries))
        result = None
        while result is None:
            try:
                result = session.get(url).json()
            except:
                continue
        return result

    def fetch_stargazers(self, repo: str, batch_count=100, page_limit=400, progress=None) -> set[str]:
        """
        Fetch stargazers of the repository
        :param repo: name (GitHub flavoured. Example: theseems/HseNotebooks)
        :param batch_count: entries per GitHub API response page
        :param page_limit: max amount of pages to fetch
        :param progress: TQDM progress if any
        :return: set of stargazers
        """
        if progress is not None:
            progress.desc = 'Fetching stargazers for ' + repo

        fixed_url_part = '{0}repos/{1}/stargazers?per_page={2}&page='.format(self._api_url, repo, str(batch_count))
        current_page = 0
        result = set()

        while True:
            if progress is not None:
                progress.set_postfix_str("page " + str(current_page + 1))
            page_response: list[dict] = self._get_request_json(fixed_url_part + str(current_page))
            if len(page_response) == 0:
                break
            if not isinstance(page_response, list):
                logging.warning(
                    F'Failure fetching stargazers for %s:'
                    F'\nRequest: {fixed_url_part + str(current_page)}'
                    F'\nUnknown response: "%s"',
                    repo,
                    json.dumps(page_response))
                continue
            for stargazer in page_response:
                result.add(stargazer["login"])
            current_page += 1
            if current_page > page_limit:
                break
        return result

    def fetch_starred_repositories(self, user, batch_count=100, page_limit=400, progress=None) -> set[str]:
        """
        Fetch repositories starred by a user
        :param user: to fetch starred repositories of
        :param batch_count: number of entries per GitHub API response's page
        :param page_limit: max amount of pages to fetch
        :param progress: TQDM progress
        :return: set of starred repositories
        """
        if progress is not None:
            progress.desc = 'Fetching starred repositories of ' + user

        fixed_url_part = '{0}users/{1}/starred?per_page={2}&page='.format(self._api_url, user, batch_count)
        current_page = 0
        result = set()

        while True:
            page_response = None
            try:
                if progress is not None:
                    progress.set_postfix_str("page " + str(current_page + 1))
                page_response: starred_response_type = self._get_request_json(fixed_url_part + str(current_page))
                if len(page_response) == 0 or ('message' in page_response and page_response['message'] == 'Not Found'):
                    break
                for repository in page_response:
                    result.add(repository["full_name"])
            except:
                if page_response is not None and \
                        'message' in page_response and \
                        'rate limit' in page_response['message']:
                    self._update_api_token()
                logging.warning('Unexpected response: ' + json.dumps(page_response))
                logging.warning('Request: ' + json.dumps(fixed_url_part + str(current_page)))
                continue
            current_page += 1
            if current_page > page_limit:
                break
        return result
