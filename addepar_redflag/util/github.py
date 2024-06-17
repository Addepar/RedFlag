import re
from requests import get
from requests.exceptions import HTTPError
from time import time, sleep
from typing import Generator

from github import GithubException, UnknownObjectException

from .console import (
    pretty_print,
    MessageType
)


def _github_request(
    url: str,
    token: str | None = None,
    params=None,
    accepted_codes=[]
):
    """Returns response for GET request to GitHub."""

    headers = {
        'Accept': 'application/vnd.github.v3+json'
    }
    if token:
        headers.update({'Authorization': f'token {token}'})

    while True:
        try:
            response = get(
                url,
                params=params,
                headers=headers
            )

            if (
                response.status_code == 403
                and response.headers['X-RateLimit-Remaining'] == '0'
            ):
                retry_at = int(response.headers['X-RateLimit-Reset'])

                pretty_print(
                    f'GitHub rate limit, retrying at [{retry_at}]',
                    MessageType.WARN
                )

                while time() < retry_at:
                    sleep(1)

                continue

            response.raise_for_status()

            return response
        except HTTPError as http_err:
            if http_err.response.status_code in accepted_codes:
                return http_err.response
            else:
                pretty_print(
                    f'HTTP error occurred: {http_err}',
                    MessageType.WARN
                )
        except Exception as err:
            pretty_print(
                f'Unexpected error occurred: {err}',
                MessageType.WARN
            )
        raise Exception('REST API request failed')


def get_pr_templates(
    repository
):
    FILE_NAME = 'pull_request_template.md'
    LOCATIONS = ['.', 'docs', '.github']
    # GitHub supports multiple templates within this directory in any of the locations
    TEMPLATE_DIRECTORY = 'PULL_REQUEST_TEMPLATE'

    templates = []
    for location in LOCATIONS:
        try: 
            for file in repository.get_contents(location):
                path = f'{location}/{file.name}'
                if file.name.lower() == FILE_NAME:
                    templates.append(path)

                if file.name.upper() == TEMPLATE_DIRECTORY:
                    templates.extend([f'{path}/{template.name}' for template in repository.get_contents(path)])
        except UnknownObjectException:
            pass

    try:
        template_texts = [repository.get_contents(template).decoded_content.decode() for template in templates]
    except GithubException as e:
        pretty_print(
            f'GitHub exception occurred: {e}',
            MessageType.FATAL
        )
        exit(1)
    return template_texts


def get_commits_in_comparison(
    url: str,
    token: str | None,
) -> Generator[dict, None, None]:
    results = _github_request(
        url=url,
        token=token,
        params={"page": 1, "per_page": 100}
    )

    for commit in results.json().get('commits'):
        yield commit

    while 'next' in results.links.keys():
        results = _github_request(
            url=results.links['next']['url'],
            token=token
        )

        for commit in results.json().get('commits'):
            yield commit


def matches_template_text(
    template: str,
    message: str
) -> bool:
    """
    GitHub adds soft line breaks that don't exist in the PR template, require extra logic to compare.

    Example

    In PR, returned from API:
    Briefly describe how the problem is fixed. Include any salient
    implementation details.

    In template file:
    Briefly describe how the problem is fixed. Include any salient implementation details.
    """
    template_lines = template.splitlines()
    message_lines = message.splitlines()
    
    try:
        message_offset = 0
        for index, line in enumerate(template_lines):
            # Github tries to be helpful and removes double spaces from lines, causing the PR comment to be different
            line = line.replace('  ', ' ').lstrip()

            # Exact match on the line
            if line == message_lines[index + message_offset].lstrip():
                continue

            # Check if there were soft breaks added
            else:
                while line:
                    if line.startswith(message_lines[index + message_offset]):
                        line = line \
                            .replace(message_lines[index + message_offset], '') \
                            .lstrip()

                        message_offset += 1
                    else:
                        return False

                # Decrease the offset back one step to re-align since we no longer need to look forward
                message_offset -= 1
        return True
    except Exception:
        return False


def filter_commit(
    title: str,
    commit: dict,
    title_regexes: list = None,
    users: list = None
) -> bool:
    if not title_regexes:
        title_regexes = []

    if not users:
        users = []

    for regex in title_regexes:
        if re.match(regex, title):
            return False

    if commit.get('commit').get('author').get('email') in users:
        return False

    return True
