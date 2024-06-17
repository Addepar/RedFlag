import re
from requests.exceptions import HTTPError

from rich.progress import Progress

from ..models.structures import Ticket
from .console import (
    pretty_print,
    MessageType
)


JIRA_REGEX = re.compile(r'[A-Z][A-Z]+-\d+')


def get_jira_ticket_from_pr_title(
    client,
    title: str,
    progress: Progress | None = None,
):
    # Try to fetch Jira ticket information from the PR title
    match = JIRA_REGEX.search(title)

    if match:
        jira_id = match.group(0)

        # If there's a match, validate it exists
        try:
            jira_ticket = client.get_issue(jira_id)

            return Ticket(
                id=jira_id,
                summary=jira_ticket.get('fields').get('summary'),
                description=jira_ticket.get('fields').get('description')
            )
        except HTTPError:
            pretty_print(
                'Failed to access Jira ticket.',
                MessageType.WARN,
                progress=progress
            )
            pass
