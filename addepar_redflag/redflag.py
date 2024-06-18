import asyncio
import json as jsonlib
import logging
from base64 import b64encode
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from re import match

from atlassian import Jira
from botocore.config import Config
from botocore.exceptions import ClientError
from github import Github, GithubException, UnknownObjectException
from jinja2 import Environment, PackageLoader, select_autoescape
from langchain.output_parsers.fix import OutputFixingParser
from langchain_community.chat_models import BedrockChat
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from rich.progress import Progress, SpinnerColumn, BarColumn, MofNCompleteColumn

from .models.prompts.response_models import Review, TestPlan
from .models.structures import Result, PullRequest
from .util.console import (
    pretty_print,
    MessageType
)
from .util.github import (
    get_pr_templates,
    get_commits_in_comparison,
    matches_template_text,
    filter_commit
)
from .util.jira import get_jira_ticket_from_pr_title
from .util.llm import (
    build_file_context,
    build_jira_block,
    build_prompt,
    MAX_PARSER_RETRIES
)


async def query_model(
    result,
    llm,
    progress: Progress,
    progress_task_id: int,
    prompts: dict
) -> None:
    # Ignore WARNING messages from urllib3
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    # Instantiate parsers
    review_parser = OutputFixingParser.from_llm(
        max_retries=MAX_PARSER_RETRIES,
        llm=llm,
        parser=PydanticOutputParser(pydantic_object=Review)
    )
    test_plan_parser = OutputFixingParser.from_llm(
        max_retries=MAX_PARSER_RETRIES,
        llm=llm,
        parser=PydanticOutputParser(pydantic_object=TestPlan)
    )

    # Build chains
    review_prompt = build_prompt(**prompts.get('review'))
    test_plan_prompt = build_prompt(**prompts.get('test_plan'))

    review_chain = review_prompt | llm | review_parser
    test_plan_chain = test_plan_prompt | llm | test_plan_parser

    # Build context
    jira_information = build_jira_block(result=result)
    file_context = build_file_context(
        result=result,
        files=result.pr.file_names
    )

    # Initialize the prompt
    prompt_input = {
        'pr_title': result.pr.title,
        'pr_description': result.pr.message,
        'num_files': len(result.pr.file_names),
        'file_names': ', '.join(result.pr.file_names),
        'additional_information': f'{jira_information}\n\n{file_context}',
        'format_instructions': review_parser.get_format_instructions(),
    }

    # Check the token count if we pass all files in the PR
    result.token_count = llm.get_num_tokens(review_prompt.format(**prompt_input))

    try:
        review_response = await review_chain \
            .with_config(run_name=result.pr.title) \
            .ainvoke(prompt_input)

        result.review = review_response
    except (ValueError, AttributeError, ClientError) as e:
        pretty_print(
            f'Failed to determine if PR should be tested for {result.pr.title} (URL: {result.pr.url}). '
            f'Please manually review. Error: {e}',
            MessageType.WARN
        )
        return

    # Only create a test plan if the PR should be reviewed
    if result.review and result.review.result:
        file_context = (
            build_file_context(result=result, files=result.review.files)
            if result.review.files
            else ''
        )

        prompt_input.update({
            'additional_information': f'{jira_information}\n\n{file_context}',
            'format_instructions': test_plan_parser.get_format_instructions(),
        })

        try:
            test_plan_response = await test_plan_chain \
                .with_config(run_name=result.pr.title) \
                .ainvoke(prompt_input)

            result.test_plan = test_plan_response
        except (ValueError, AttributeError, ClientError) as e:
            pretty_print(
                f'Failed to create a test plan for {result.pr.title} (URL: {result.pr.url}). '
                f'Please manually review. Error: {e}',
                MessageType.WARN
            )

    if progress:
        progress.update(
            progress_task_id,
            advance = 1
        )


async def redflag(
    github: Github,
    jira: Jira,
    config: dict,
):
    try:
        repository = github.get_repo(config.get('repo'))
    except GithubException as e:
        pretty_print(
            f'GitHub exception occurred: {e}',
            MessageType.FATAL
        )
        exit(1)

    template_texts = get_pr_templates(repository)
    to_commit = config.get('to')
    from_commit = config.get('from')
    max_results = config.get('max_commits')
    progress_bar = config.get('progress_bar')

    time = datetime.now()
    metadata = {
        'repository': repository.full_name,
        'repository_url': repository.html_url,
        'date': time.strftime('%b  %d, %Y'),
        'jira_url': jira.url if jira else '',
        'link_text': None,
        'link_url': None,
        'commits': {
            'from': '',
            'to': ''
        }
    }

    results = []

    # If it's a single commit
    if not from_commit:
        if match('^[a-f0-9]{40}$', to_commit):
            from_commit = repository.get_commit(sha=to_commit)
            lines = from_commit.commit.message.splitlines()
            title, message = lines[0], '\n'.join(lines[2:])
            pr = PullRequest(
                repository=repository.full_name,
                title=title,
                message=message,
                url=from_commit.html_url,
                files=from_commit.files,
                strip_lines=config.get('strip_description_lines'),
                strip_html_comments=config.get('strip_html_comments')
            )
        else:
            from_commit = repository.get_pull(int(to_commit))
            pr = PullRequest(
                repository=repository.full_name,
                title=from_commit.title,
                message=from_commit.body,
                url=from_commit.html_url,
                files=list(from_commit.get_files()),
                strip_lines=config.get('strip_description_lines'),
                strip_html_comments=config.get('strip_html_comments')
            )

        metadata.update({
            'link_text': to_commit,
            'link_url': pr.url,
            'commits': {'from': to_commit, 'to': to_commit}
        })

        result = Result(pr=pr)
        if jira:
            result.ticket = get_jira_ticket_from_pr_title(
                jira,
                pr.title
            )

        results.append(result)

        pretty_print(
            'Retrieved PRs',
            MessageType.SUCCESS
        )
    else:
        try:
            # Get all commits between from and to
            compare = repository.compare(from_commit, to_commit)

            # If there are no commits, try the other way around
            if not compare.ahead_by:
                compare = repository.compare(to_commit, from_commit)
                
                # If we can't find anything, exit
                if not compare.ahead_by:
                    pretty_print(
                        'No PRs to evaluate, exiting.',
                        MessageType.FATAL
                    )
                    exit(0)
        except UnknownObjectException as e:
            pretty_print(
                f'Failed to find the to and from refs: {e}',
                MessageType.FATAL
            )
            exit(1)

        # Flag for truncating SHA hashes in link text
        to_hash = match('^[a-f0-9]{40}$', to_commit)
        from_hash = match('^[a-f0-9]{40}$', from_commit)

        short_to_name = to_commit if not to_hash else to_commit[:8]
        short_from_name = from_commit if not from_hash else from_commit[:8]

        metadata.update({
            'link_text': f'{short_from_name}...{short_to_name}',
            'link_url': compare.html_url,
            'commits': {'from': f'{short_from_name}', 'to': f'{short_to_name}'}
        })

        # PyGithub caps at 250 commits, so we need a custom iterator
        commits = get_commits_in_comparison(
            url=compare.url,
            token=config.get('github_token')
        )

        progress_count = compare.ahead_by
        if max_results:
            progress_count = max_results if max_results < progress_count else progress_count

        # Create progress bar
        progress_task_id = 0
        progress = nullcontext()
        if progress_bar:
            progress = Progress(
                SpinnerColumn(),
                "[progress.description]{task.description}",
                BarColumn(),
                MofNCompleteColumn(),
                transient=True
            )

            progress_task_id = progress.add_task(
                f'Retrieving {progress_count} PRs',
                total=progress_count
            )

        # Iterate over commits and create PR objects
        count = 0
        with progress:
            for commit in commits:
                lines = commit \
                    .get('commit') \
                    .get('message') \
                    .splitlines()

                # Commit title is always the first line. The text, if it exists, starts from the 3rd
                title, message = lines[0], '\n'.join(lines[2:])

                # Some commits we never care about
                if not filter_commit(
                    title,
                    commit,
                    title_regexes=config.get('filter_commits').get('titles'),
                    users=config.get('filter_commits').get('users')
                ):
                    continue

                if template_texts and message:
                    for template_text in template_texts:
                        if matches_template_text(
                            template_text,
                            message
                        ):
                            # If it's using the templated message, it tells us nothing
                            message = ''
                            break

                commit_files = repository \
                    .get_commit(sha=commit.get('sha')) \
                    .files

                # Skip if there aren't any file changes, happens with some merges
                if not commit_files:
                    continue

                pr = PullRequest(
                    repository=repository.full_name,
                    title=title,
                    message=message,
                    url=commit.get('html_url'),
                    files=commit_files,
                    strip_lines=config.get('strip_description_lines'),
                    strip_html_comments=config.get('strip_html_comments')
                )

                result = Result(pr=pr)
                if jira:
                    result.ticket = get_jira_ticket_from_pr_title(
                        jira,
                        title,
                        progress=progress
                    )

                results.append(result)
                count += 1
                if max_results:
                    if count == max_results:
                        break
                
                if progress_bar:
                    progress.update(
                        progress_task_id,
                        advance=1
                    )

        pretty_print(
            f'Retrieved {progress_count} PRs',
            MessageType.SUCCESS
        )

    # Instantiate Bedrock
    llm = BedrockChat(
        region_name=config.get('bedrock', {}).get('region') or None,
        credentials_profile_name=config.get('bedrock', {}).get('profile') or None,
        model_id=config.get('bedrock', {}).get('model_id'),
        model_kwargs={
            'max_tokens': 4096,
            'temperature': 0.0
        },
        config=Config(
            read_timeout=600,
            retries={'max_attempts': 10, 'mode': 'adaptive'}
        )
    )

    pretty_print(
        'Instantiated Bedrock',
        MessageType.SUCCESS
    )
    
    # Create progress bar
    progress_task_id = 0
    progress = nullcontext()
    if progress_bar:
        progress = Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            MofNCompleteColumn(),
            transient=True
        )

        progress_task_id = progress.add_task(
            'Evaluating PRs',
            total=len(results)
        )

    # Create tasks
    prompts = config.get('prompts')
    tasks = [
        asyncio.create_task(query_model(
            result=result,
            llm=llm,
            progress=progress if progress_bar else None,
            progress_task_id=progress_task_id,
            prompts=prompts
        )) for result in results
    ]
    
    # Run all the tasks (blocking)
    try:
        with progress:
            await asyncio.gather(*tasks)
    except Exception as e:
        pretty_print(
            f'Failed to evaluate against LLM, exception: {e}',
            MessageType.FATAL
        )
        exit(1)

    pretty_print(
        'Evaluated PRs',
        MessageType.SUCCESS
    )

    errored = []
    in_scope = []
    out_of_scope = []

    # Work out what should and should not be in scope
    for result in results:
        if hasattr(result, 'review'):
            if result.review.result:
                if hasattr(result, 'test_plan'):
                    in_scope.append(result)
                else:
                    # Test Plan failed to create
                    errored.append(result)
            else:
                out_of_scope.append(result)
        else:
            errored.append(result)

    percent = (len(in_scope) / len(results)) * 100 if len(results) > 0 else 0.0
    pretty_print(
        f'Evaluated {len(results)} entries. {len(in_scope)} are in scope ' \
        f'({(len(in_scope) / len(results)) * 100 if len(results) > 0 else 0}%).',
        MessageType.SUCCESS
    )

    # Generate output
    base_filename = to_commit if not from_commit else f'{metadata["commits"]["from"]}-{metadata["commits"]["to"]}'
    filename = f'{repository.full_name.replace("/", "_")}-{base_filename.replace("/", "-")}-{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}'

    jinja = Environment(
        loader=PackageLoader("addepar_redflag"),
        autoescape=select_autoescape()
    )

    html_template = jinja.get_template('results.html.jinja2')

    # Convert results to b64 for the HTML report.
    # Output in b64 to avoid tags like '</script>' from breaking the page.
    results = {
        'in_scope_b64': b64encode(jsonlib.dumps([result.to_dict() for result in in_scope]).encode('utf-8')).decode('utf-8'),
        'out_of_scope_b64': b64encode(jsonlib.dumps([result.to_dict() for result in out_of_scope]).encode('utf-8')).decode('utf-8'),
        'metadata_b64': b64encode(jsonlib.dumps(metadata).encode('utf-8')).decode('utf-8')
    }

    pretty_print(
        'Compiled results',
        MessageType.SUCCESS
    )

    # Try to create output_dir if it doesn't exist
    output_dir = config.get('output_dir')
    if output_dir:
        try:
            Path(output_dir).mkdir(
                exist_ok=True,
                parents=True
            )
        except Exception as e:
            pretty_print(
                f'Could not create output directory "{output_dir}"',
                MessageType.FATAL
            )
            exit(1)

    # Write HTML output
    if config.get('output_html'):
        file_path = Path(output_dir or '.') / f'{filename}.html'
        with open(file_path, 'w') as f:
            f.write(html_template.render(results=results))

            pretty_print(
                f'Wrote HTML report to {file_path}',
                MessageType.SUCCESS
            )

     # Write JSON output for in-scope items only
    if config.get('output_json'):
        if in_scope:
            file_path = Path(output_dir or '.') / f'{filename}.json'
            with open(file_path, 'w') as f:
                f.write(jsonlib.dumps({'in_scope': [result.to_dict() for result in in_scope], 'out_of_scope': [result.to_dict() for result in out_of_scope]}))

                pretty_print(
                    f'Wrote JSON output to {file_path}',
                    MessageType.SUCCESS
                )

    if errored:
        file_path = Path(output_dir or '.') / f'Errors-{filename}.json'
        with open(file_path, 'w') as f:
            f.write(jsonlib.dumps([result.to_dict() for result in errored]))

        pretty_print(
            f'Wrote error information to {file_path}',
            MessageType.SUCCESS
        )

    pretty_print(
        'Complete!',
        MessageType.SUCCESS
    )
