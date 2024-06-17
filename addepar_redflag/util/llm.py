from itertools import zip_longest
from textwrap import dedent

from langchain.prompts import PromptTemplate
from rich.table import Column, Table
from rich.text import Text

from ..models.structures import Result
from .console import CONSOLE


MAX_PARSER_RETRIES = 5

# Claude was trained on XML formatted data.  
# Using XML-style tags significantly increases its ability to interpret what data is where.
DEFAULT_ROLE = (
    'You are an application security engineer subject matter expert. '
    'You are tasked with determining what functionality should be penetration tested by our offensive security team for the next application version. '
    'Read the following information carefully, because you will be asked questions about it.'
)
DEFAULT_REVIEW_QUESTION = (
    'Tell me if this pull request should be included in an offensive security penetration test, or if it can be ignored. '
    'If the pull request should be included in the penetration test, include a list of files chosen from the ones in the pull request, that should be included in the penetration test. '
    'Use the information provided when making your decisions, do not make assumptions. '
    'Pull requests that only have minor changes to database schema, infrastructure, build processes, or code/unit testing can be ignored. '
    'Pull requests that add new API routes should always be reviewed to ensure that they have proper controls. '
    'The offensive security team has limited resources, so make your recommendation carefully.'
)
DEFAULT_TEST_PLAN_QUESTION = (
    'Create a penetration testing plan for the offensive security team. '
    'The plan should consist of step-by-step instructions based on the information provided that the offensive security team can use to identify vulnerabilities. '
    'Include specific details about what to test, such as HTTP methods, API routes, function/class names, and areas of interest. '
    'Do not include instructions that would be handled by the developers or quality assurance team, such as verifying that a feature works as expected or validating unit tests.'
)
PR_BLOCK = dedent(
    '''\
        Here is a single pull request, inside <pr></pr> XML tags:
        <pr>
        <title>{pr_title}</title>
        <description>{pr_description}</description>
        {num_files} total changed files: <file_names>{file_names}</file_names>
        </pr>

        {additional_information}'''
)


def build_question(question: str) -> str:
    return dedent(
        f'''\
        Here is the question, between <question></question> tags:
        <question>
        {question}
        </question>
        
        Write out your reasoning in a step-by-step manner to be sure that your conclusion is correct. Avoid simply stating the correct answer at the outset.'''
    )


def build_jira_block(result: Result) -> str:
    info = ''
    
    if result.ticket:
        info = (
            'Here is the associate Jira ticket, included between <jira></jira> tags:\n\n'
            '<jira>\n'
            f'<ticket_title>{result.ticket.id} - {result.ticket.summary}</ticket_title>'
        )

        if result.ticket.description:
            info = (
                f'{info}\n'
                f'<ticket_description>{result.ticket.description}</ticket_description>'
            )

        info = f'{info}\n</jira>'

    return info


def build_file_context(result: Result, files: list) -> str:
    context = ''

    if files:
        context = (
            'Here are the pull requests changes, included between <changes></changes> tags:\n\n'
            '<changes>\n'
        )

        for file in files:
            # Make sure the file requested exists
            if file in result.pr.file_names:
                index = result.pr.file_names.index(file)
                patch = result.pr.files[index].patch
                context = (
                    f'{context}<file_name>{file}</file_name><patch>{patch}</patch>\n'
                )
        
        context = f'{context}</changes>'
    
    return context


def build_prompt(role: str, question):
    return PromptTemplate.from_template(
        f'{role}\n\n'
        f'{PR_BLOCK}\n\n'
        f'{question}\n\n'
        '{format_instructions}'
    )

# The LLM likes to use lists when asked to provide information in a detailed format, even though the field is for a string.
# Using a validation function helps prevent retry calls
def convert_to_string(cls, v):
    if isinstance(v, list):
        return '\n'.join([line.rstrip() for line in v])
    return v


def build_evaluation_result(result, response, should_print: bool = False):
    """
    Commit[:8]… Title
    Review | Verdict | Review Reasoning | Verdict Reasoning
    True | Correct | This pull request... | The question asks...
    """
    commit = result.pr.url.split('/')[-1]
    table = Table(
        Column(header='Review'),
        Column(header='Verdict'),
        Column(header='Review Reasoning'),
        Column(header='Verdict Reasoning'),
        title=f'[cyan]{commit[:8]}…[/cyan] {result.pr.title}'
    )

    verdict = response.get('value')
    is_correct = verdict.upper() == 'CORRECT'
    verdict = Text(verdict, style='green') if is_correct else Text(verdict, style='red')
    review = ':white_check_mark: [bold green]Yes[/bold green]' if result.review.result else ':x: [bold red]No[/bold red]'
    table.add_row(review, response.get('value'), result.review.reasoning, response.get('reasoning'))

    if should_print:
        CONSOLE.print(table, end='\n\n')
    return table


def pretty_print_evaluation_table(results, review_eval_responses):
    """
    Evaluation Results
    Result | Commit | LLM Verdict | Reference
    Correct | aaaa | Correct | Yes, ...
    False Positive | bbbb | Incorrect | No, ...
    False Negative | cccc | Incorrect | Yes, ...
    """
    table = Table(
        Column(header='Result'),
        Column(header='Commit', width=8, style='cyan'),
        Column(header='LLM Verdict'),
        Column(header='Reference'),
        title='Evaluation Results',
        show_lines=True
    )

    correct_cases = []
    false_positive_cases = []
    false_negative_cases = []

    for result, response in zip(results, review_eval_responses):
        commit = result.pr.url.split('/')[-1]
        verdict = response.get('result').get('value')
        is_correct = verdict.upper() == 'CORRECT'
        verdict = Text(verdict, style='green') if is_correct else Text(verdict, style='red')
        status = ':white_check_mark: [bold green]Correct[/bold green]'
        if is_correct:
            correct_cases.append(commit)
        else:
            if result.review.result:
                status = ':x: [bold red]False Positive[/bold red]'
                false_positive_cases.append(commit)
            else:
                status = ':x: [bold red]False Negative[/bold red]'
                false_negative_cases.append(commit)

        table.add_row(status, commit, verdict, response.get('reference'))

    CONSOLE.print(table)


    """
    Correct | False Positive | False Negative
    Commit  | Commit         | Commit 
    n       | n              | n
    """
    table = Table(
        Column(header=':white_check_mark: [bold green]Correct[/bold green]', width=40, style='cyan', footer=str(len(correct_cases))),
        Column(header=':x: [bold red]False Positive[/bold red]', width=40, style='cyan', footer=str(len(false_positive_cases))),
        Column(header=':x: [bold red]False Negative[/bold red]', width=40, style='cyan', footer=str(len(false_negative_cases))),
        show_footer=True
    )

    for correct, positive, negative in zip_longest(correct_cases, false_positive_cases, false_negative_cases):
        table.add_row(correct or '', positive or '', negative or '')

    CONSOLE.print(table)
