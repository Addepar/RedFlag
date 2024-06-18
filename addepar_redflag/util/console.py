from enum import Enum

from rich import print as rprint
from rich.console import Console
from rich.progress import Progress
from rich.style import Style
from rich.table import Table


CONSOLE = Console()
CONFIG_VALUE_MAX_LEN = 30


# Define the message types
class MessageType(Enum):
    SUCCESS = "success"
    WARN = "error"
    FATAL = "fatal"
    INFO = "info"

# Define the styles with emojis
styles = {
    MessageType.SUCCESS: Style(color="green", bold=False),
    MessageType.WARN: Style(color="yellow", bold=False),
    MessageType.FATAL: Style(color="red", bold=False, underline=True),
    MessageType.INFO: Style(color="blue", bold=False)
}

# Define the emojis
emojis = {
    MessageType.SUCCESS: ":white_check_mark:",  # ✅
    MessageType.WARN: ":warning:",              # ⚠️
    MessageType.FATAL: ":x:",                   # ❌
    MessageType.INFO: ":information_source:"    # ℹ️
}


def str2bool(string: str) -> bool:
    if string is None:
        return False

    return string.lower() in ('yes', 'true', 't', 'y', '1')


# Helper function for standard formatting
def pretty_print_header():
    CONSOLE.print(
        "Starting [bold]RedFlag 🚩[/bold]",
        style=Style()
    )


# Helper function for standard formatting
def pretty_print(
        message: str,
        message_type: MessageType = MessageType.INFO,
        json: bool = False,
        progress: Progress | None = None
):
    console = CONSOLE
    if progress:
        console = progress.console

    if message_type in styles and message_type in emojis:
        emoji = emojis[message_type]
        if not json:
            console.print(
                f"{emoji} {message}",
                style=styles[message_type]
            )
        else:
            console.print_json(
                f"{message}"
            )
    else:
        console.print(message)


def pretty_print_traceback():
    CONSOLE.print_exception()


def pretty_print_config_table(
    heritage: dict,
    config: dict
):    
    table = Table(title="")
    table.add_column("Configuration Option", no_wrap=True)
    table.add_column("Value")
    table.add_column("Source")

    secret_keys = ["github_token", "jira.token"]
    hidden_items = ["command"]

    def add_row(table, key, value, parent_key = None):
        full_key = f"{parent_key}.{key}" if parent_key else key

        # Recurse
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                add_row(table, sub_key, sub_value, full_key)
        else:
            # Hide secrets
            if full_key in secret_keys:
                if value is not None:
                    value = "*" * len(value)

            # Prettify None values
            if value is None:
                value = "-"

            # Get a string representation
            value = str(value)

            # Find config source
            heritage_keys = full_key.split('.')
            heritage_value = heritage
            for k in heritage_keys:
                try: heritage_value = heritage_value[k]
                except: pass
            
            # Restrict value length
            if len(value) > CONFIG_VALUE_MAX_LEN:
                value = value[:CONFIG_VALUE_MAX_LEN - 3] + '...'

            table.add_row(full_key, value, heritage_value)

    for key, value in config.items():
        if key not in hidden_items:
            add_row(table, key, value)

    rprint(table)


def pretty_print_dict_as_table(
    data: dict,
    key_title: str = "Key",
    value_title: str = "Value",
    title: str = "Table Title"
):
    table = Table(title=title)
    table.add_column(key_title, style="cyan", no_wrap=True)
    table.add_column(value_title, style="magenta")

    def add_row(table, key, value, parent_key):
        full_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                add_row(table, sub_key, sub_value, full_key)
        else:
            table.add_row(full_key, str(value))

    for key, value in data.items():
        add_row(table, key, value, '')

    rprint(table)
