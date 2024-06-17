from boto3 import Session, client
from botocore.exceptions import ProfileNotFound

from .console import (
    pretty_print,
    MessageType
)


def validate_aws_credentials(profile: str) -> str:
    if profile:
        try:
            sts = Session(profile_name=profile).client('sts')
            sts.get_caller_identity()
        except ProfileNotFound as e:
            pretty_print(f'Failed to validate AWS credentials: {e}. Retrying using environment variables.', MessageType.WARN)
            profile = ''
        except Exception as e:
            pretty_print(f'Failed to validate AWS credentials: {e}', MessageType.FATAL)
            exit(1)

    if not profile:
        try:
            sts = client('sts')
            sts.get_caller_identity()
        except Exception as e:
            pretty_print(f'Failed to validate AWS credentials: {e}', MessageType.FATAL)
            exit(1)

    pretty_print('AWS credentials validated', MessageType.SUCCESS)
    return profile
