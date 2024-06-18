import yaml
from os import getenv
from pathlib import Path

from .console import (
    pretty_print,
    pretty_print_config_table,
    MessageType
)
from .llm import (
    DEFAULT_ROLE,
    DEFAULT_REVIEW_QUESTION,
    DEFAULT_TEST_PLAN_QUESTION
)

def _update_nested_dict(
    base,
    updates,
    heritage,
    heritage_source,
    allow_none=True,
    heritage_only=False
):
    for key, value in updates.items():
        if isinstance(value, dict):
            if not key in base:
                base[key] = dict()
            if not key in heritage:
                heritage[key] = dict()

            _update_nested_dict(
                base[key],
                value,
                heritage[key],
                heritage_source,
                allow_none,
                heritage_only
            )
        else:
            if allow_none or value is not None:
                heritage[key] = heritage_source
                
                if not heritage_only:
                    base[key] = value

            if heritage_source == "Default" and value is None:
                heritage[key] = "-"


def get_default_config():
    return {
        'github_token': None,
        'output_dir': 'results',
        'debug_llm': False,
        'progress_bar': True,
        'output_html': True,
        'output_json': True,
        'dataset': None,
        'repo': None,
        'max_commits': 0,
        'to': None,
        'from': None,
        'strip_html_comments': True,
        'strip_description_lines': None,
        'jira': {
            'url': None,
            'user': None,
            'token': None,
        },
        'bedrock': {
            'region': 'us-west-2',
            'profile': None,
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0'
        },
        'prompts': {
            'review': {
                'role': DEFAULT_ROLE,
                'question': DEFAULT_REVIEW_QUESTION,
            },
            'test_plan': {
                'role': DEFAULT_ROLE,
                'question': DEFAULT_TEST_PLAN_QUESTION,
            }
        },
        'filter_commits': {
            'title': None,
            'user': None
        }
    }


def get_final_config(cli_args):
    # Default configuration
    current_config = get_default_config()
    config_heritage = dict()
    _update_nested_dict(
        base=current_config,
        updates=current_config,
        heritage=config_heritage,
        heritage_source="Default",
        heritage_only=True
    )

    # Override default config with values from the config file
    config_file_path = cli_args.config
    config_file = Path(config_file_path) if config_file_path else None
    if config_file and config_file.is_file() and config_file.exists():
        # Print which configuration file we parsed
        pretty_print(
            f'Using configuration file: {str(config_file.absolute())}',
            MessageType.INFO
        )

        # Load config file
        file_config = yaml.safe_load(config_file.read_text())
        if file_config:
            _update_nested_dict(
                base=current_config,
                updates=file_config,
                heritage=config_heritage,
                heritage_source="Config File"
            )
    else:
        if not config_file_path:
            pretty_print(
                f'No configuration file specified',
                MessageType.INFO
            )
        else:
            pretty_print(
                f'Configuration file not found: {str(config_file.absolute())}',
                MessageType.WARN
            )

    # Override current config with values from the environment variables
    env_overrides = {
        'github_token': getenv('RF_GITHUB_TOKEN'),
        'output_dir': getenv('RF_OUTPUT_DIR'),
        'dataset': getenv('RF_DATASET'),
        'repo': getenv('RF_REPO'),
        'max_commits': int(getenv('RF_MAX_COMMITS')) if getenv('RF_MAX_COMMITS') else None,
        'to': getenv('RF_TO'),
        'from': getenv('RF_FROM'),
        'jira': {
            'url': getenv('RF_JIRA_URL'),
            'user': getenv('RF_JIRA_USER'),
            'token': getenv('RF_JIRA_TOKEN')
        },
        'bedrock': {
            'region': getenv('RF_BEDROCK_REGION'),
            'profile': getenv('RF_BEDROCK_PROFILE'),
            'model_id': getenv('RF_BEDROCK_MODEL_ID')
        }
    }

    _update_nested_dict(
        base=current_config,
        updates=env_overrides,
        heritage=config_heritage,
        heritage_source="Env Var",
        allow_none=False
    )
    
    # Override current config with values from the CLI args
    cli_dict = dict()
    nested_keys = ['jira', 'bedrock']
    default_config = get_default_config()
    for key, value in vars(cli_args).items():
        if value is not None:
            keys = key.split('_')
            root, param = keys[0], '_'.join(keys[1:])
            sub_config = cli_dict
            if root in nested_keys:
                sub_config = sub_config.setdefault(root, {})
                sub_config[param] = value
            else:
                # Don't store CLI value for default config values
                if type(value) == bool:
                    if key in default_config and default_config[key] == value:
                        continue

                sub_config[key] = value

    _update_nested_dict(
        base=current_config,
        updates=cli_dict,
        heritage=config_heritage,
        heritage_source="CLI Param"
    )

    # Print the configuration table
    pretty_print_config_table(
        heritage=config_heritage,
        config=current_config
    )

    _validate_config(current_config.get("command"), current_config)

    return current_config


def _validate_config(command, config):
    """Some arguments are required, but since they can be 
    derived from multiple sources they may not be specified through the CLI."""
    required = [('github_token', 'GitHub PAT'), ('bedrock.model_id', 'Bedrock Model ID'), ('bedrock.region', 'Bedrock Region')]
    
    # "Eval" mode
    if command == 'eval':
        required.extend([('dataset', 'Dataset')])

    # Default mode
    else:
        required.extend([('repo', 'Repository'), ('to', 'To')])

    missing = []
    for param, pretty in required:
        keys = param.split('.')
        value = config
        for key in keys:
            value = value.get(key)
        if not value:
            missing.append(pretty)

    if missing:
        pretty_print(
            f'{", ".join(missing)} {"is" if len(missing) == 1 else "are"} required for this operation.',
            MessageType.FATAL
        )
        exit(1)
