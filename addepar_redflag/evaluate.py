import asyncio
import json
import logging
from contextlib import nullcontext
from pathlib import Path

from atlassian import Jira
from botocore.config import Config
from github import Github, GithubException
from langchain.evaluation import load_evaluator
from langchain.output_parsers.fix import OutputFixingParser
from langchain_community.chat_models import BedrockChat
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from rich.progress import Progress, SpinnerColumn, BarColumn, MofNCompleteColumn

from .models.prompts.response_models import Review
from .models.structures import PullRequest, Result
from .util.console import (
    pretty_print,
    MessageType
)
from .util.jira import get_jira_ticket_from_pr_title
from .util.llm import (
    build_evaluation_result,
    build_file_context,
    build_jira_block,
    build_prompt,
    pretty_print_evaluation_table,
    build_evaluation_result,
    MAX_PARSER_RETRIES
)


async def review_evaluation(
    result: Result,
    llm,
    progress: Progress,
    progress_task_id: int,
    evaluator,
    should_review: bool,
    reference: str,
    prompts: dict
) -> dict:
    review_parser = OutputFixingParser.from_llm(
        max_retries=MAX_PARSER_RETRIES,
        llm=llm,
        parser=PydanticOutputParser(pydantic_object=Review)
    )
    review_prompt = build_prompt(**prompts.get('review'))
    review_chain = review_prompt | llm | review_parser
    jira_information = build_jira_block(result=result)

    file_context = build_file_context(
        result=result,
        files=result.pr.file_names
    )

    prompt_input = {
        'pr_title': result.pr.title,
        'pr_description': result.pr.message,
        'num_files': len(result.pr.file_names),
        'file_names': ', '.join(result.pr.file_names),
        'additional_information': f'{jira_information}\n\n{file_context}',
        'format_instructions': review_parser.get_format_instructions()
    }

    # Check the token count if we pass all files in the PR.
    result.token_count = llm.get_num_tokens(review_prompt.format(**prompt_input))

    llm_response = await review_chain \
        .with_config(run_name=result.pr.title) \
        .ainvoke(prompt_input)

    # Set attributes on result based on response object
    setattr(result, 'review', llm_response)

    prediction = (
        f'{"Yes, this PR should be tested." if llm_response.result else "No, this PR should not be tested."}\n'
        f'Student Logic: {llm_response.reasoning}'
        f'Relevant Files: {llm_response.files}'
    )

    # Passing in file context isn't needed by the evaluator and the response isn't parsed by pydantic.
    # Passing in too much information confuses the evaluator and can cause it to use the "student"
    # reasoning or otherwise disregard the context.
    prompt_input.update(
        {'additional_information': jira_information, 'format_instructions': ''}
    )
        
    reference = f'Yes, this PR should be tested. {reference}' if should_review else f'No, this PR should not be tested. {reference}'

    eval_response = await evaluator.aevaluate_strings(
        input=review_prompt.format(**prompt_input),
        prediction=prediction,
        reference=reference
    )

    if progress:
        progress.update(progress_task_id, advance=1)
        table = build_evaluation_result(result, eval_response, should_print=False)
        progress.console.print(table, end='\n\n')
    else:
        build_evaluation_result(result, eval_response, should_print=True)
    

    return {'reference': reference, 'result': eval_response}


async def do_evaluations(
    github: Github,
    jira: Jira,
    dataset: Path,
    config: dict
):    
    # Avoid WARNING messages from urllib3
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    # Load the dataset
    pretty_print(
        f'Using dataset {dataset.resolve()}.',
        MessageType.INFO
    )

    try:
        with dataset.open() as file:
            dataset = json.load(file)
            
            pretty_print(
                f'Loaded dataset with {len(dataset)} commits.',
                MessageType.INFO
            )
    except Exception as e:
        pretty_print(
            f'Unable to open dataset, exception: {e}',
            MessageType.FATAL
        )
        exit(1)

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

    # Create Langchain evaluator
    evaluator = load_evaluator(
        evaluator='cot_qa',
        llm=llm
    )

    # Build result objects and kick off evaluations from the dataset
    results = []
    tasks = []

    # Create and start task creation progress bar
    progress_task_id = 0
    progress = nullcontext()
    progress_bar = config.get('progress_bar')
    if progress_bar:
        progress = Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            MofNCompleteColumn(),
            transient=True
        )
        progress_task_id = progress.add_task(
            'Creating tasks',
            total=len(dataset)
        )

    # Create LLM evaluation progress bar we can pass to tasks
    progress_llm_task_id = 0
    progress_llm = nullcontext()
    if progress_bar:
        progress_llm = Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            MofNCompleteColumn(),
            transient=True
        )
        progress_llm_task_id = progress_llm.add_task(
            'Evaluating commits',
            total=len(dataset)
        )
        
    # Retrieve all PRs and corresponding Jira tickets and create tasks
    task_exception = None
    with progress:
        try:
            for data in dataset:
                repository = github.get_repo(data.get('repository'))
                
                target = repository.get_commit(sha=data.get('commit'))
                lines = target.commit.message.splitlines()
                title, message = lines[0], '\n'.join(lines[2:])

                pr = PullRequest(
                    repository=repository.full_name,
                    title=title,
                    message=message,
                    url=target.html_url,
                    files=target.files,
                    strip_lines=config.get('strip_description_lines'),
                    strip_html_comments=config.get('strip_html_comments')
                )

                result = Result(pr)

                if jira:
                    result.ticket = get_jira_ticket_from_pr_title(
                        jira,
                        pr.title
                    )

                # Create task
                prompts = config.get('prompts')
                tasks.append(
                    asyncio.create_task(
                        review_evaluation(
                            result=result,
                            llm=llm,
                            progress=progress_llm if progress_bar else None,
                            progress_task_id=progress_llm_task_id,
                            evaluator=evaluator,
                            should_review=data.get('should_review'),
                            reference=data.get('reference'),
                            prompts=prompts
                        )
                    )
                )

                # Store PR and Jira information in results list
                results.append(result)

                # Update progress bar
                if progress_bar:
                    progress.update(
                        progress_task_id,
                        advance=1
                    )

        except GithubException as e:
            task_exception = (
                f'GitHub exception occurred: {e}',
                MessageType.FATAL
            )
    
    # A handled exception occurred
    if task_exception:
        pretty_print(*task_exception)
        exit(1)

    pretty_print(
        'Created tasks',
        MessageType.SUCCESS
    )

    # Evaluate tasks
    try:
        with progress_llm:
            review_eval_responses = await asyncio.gather(*tasks)
    except ValueError as e:
        pretty_print(
            f'Failed to evaluate against LLM, exception: {e}',
            MessageType.FATAL
        )

        exit(1)

    pretty_print(
        'Evaluated commits',
        MessageType.SUCCESS
    )
    
    pretty_print_evaluation_table(results, review_eval_responses)