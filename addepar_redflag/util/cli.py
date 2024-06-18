import argparse
import asyncio
from pathlib import Path
from sys import exit
from atlassian import Jira
from dotenv import load_dotenv
from github import Auth, Github
from langchain.globals import set_debug

from ..evaluate import do_evaluations
from ..redflag import redflag
from .aws import validate_aws_credentials
from .config import (
    get_default_config,
    get_final_config
)
from .console import (
    pretty_print,
    pretty_print_header,
    pretty_print_traceback,
    MessageType
)


def common_arguments(parser, default_config):
    parser.add_argument('--config', help='The path to the configuration file.')
    parser.add_argument('--debug-llm', action='store_true', dest='debug_llm', help=f'Flag to enable debug LLM output.')
    parser.add_argument('--github-token', help='GitHub PAT to authenticate to the GitHub API.')
    parser.add_argument('--jira-user', help='Jira Username to authenticate to the Jira API.')
    parser.add_argument('--jira-token', help='Jira PAT to authenticate to the Jira API.')
    parser.add_argument('--jira-url', help='The URL for the Jira API.')
    parser.add_argument('--bedrock-region', help='The AWS Region to use for Bedrock. If not set, will fall back to AWS defaults.')
    parser.add_argument('--bedrock-profile', help='The AWS Profile to use for Bedrock. If not set, will fall back to AWS defaults.')
    parser.add_argument('--bedrock-model-id', help=f'The Bedrock model to use. (default: {default_config["bedrock"]["model_id"]})')
    parser.add_argument('--no-progress-bar', action='store_false', dest='progress_bar', help='Flag to not display a progress bar.')
    parser.add_argument('--no-strip-html-comments', action='store_false', dest='strip_html_comments', help='Flag to not strip HTML comments from PR descriptions.')


def cli():
    pretty_print_header()

    # Load env var file, if present
    load_dotenv()

    # Get defaults
    default_config = get_default_config()

    # Parent parser
    parser = argparse.ArgumentParser(prog='redflag', description='RedFlag CLI')
    parser.add_argument('--output-dir', help=f'The output directory for reports. (default: {default_config["output_dir"]})')
    parser.add_argument('--repo', help='The GitHub repository to test against.')
    parser.add_argument('--to', help='The target commit SHA, branch, or tag to compare against.')
    parser.add_argument('--from', help='The source commit SHA, branch, or tag to compare from.')
    parser.add_argument('--max-commits', type=int, help=f'The max number of commits to feed to the LLM. (default: {default_config["max_commits"]})')
    parser.add_argument('--no-output-html', action='store_false', dest='output_html', help='Flag to not output the results as HTML.')
    parser.add_argument('--no-output-json',  action='store_false', dest='output_json', help='Flag to not output the results as JSON.')
    common_arguments(parser, default_config)

    # Eval subparser
    subparsers = parser.add_subparsers(dest='command', required=False)
    evaluate_parser = subparsers.add_parser('eval', help='Run in Evaluation Mode.')
    evaluate_parser.add_argument('--dataset', help=f'The path to a file containing the dataset to use for evaluation.')
    common_arguments(evaluate_parser, default_config)

    # Parse args and get final config dict
    args = parser.parse_args()
    final_config = get_final_config(args)

    # Validate Bedrock configuration
    final_config['bedrock']['profile'] = validate_aws_credentials(final_config['bedrock']['profile'])
    
    # Instantiate GitHub object
    github_token = final_config['github_token']
    auth = Auth.Token(github_token) if github_token else None
    github = Github(
        auth=auth,
        per_page=100
    )

    # Instantiate jira object
    jira = None
    if final_config['jira']['url']:
        jira_user = final_config['jira']['user']
        jira_token = final_config['jira']['token']

        if not (jira_user and jira_token):
            pretty_print(
                'Jira credentials are required for this operation. To skip the Jira integration, leave --jira-url blank.',
                MessageType.FATAL
            )
            exit(1)
            
        jira = Jira(
            url=final_config['jira']['url'],
            username=jira_user,
            password=jira_token
        )

    # Debug LLM output
    if final_config['debug_llm']:
        set_debug(True)

    # Run the desired command
    try:
        if args.command == 'eval':
            dataset = Path(final_config['dataset'])
            asyncio.run(do_evaluations(
                github=github,
                jira=jira,
                dataset=dataset,
                config=final_config
            ))
        else:
            asyncio.run(redflag(
                github=github,
                jira=jira,
                config=final_config
            ))

    # Unhandled exception handler
    except Exception as e:
        pretty_print(
            f'An unhandled exception occurred: {e}',
            MessageType.FATAL
        )
        pretty_print_traceback()
        exit(1)
